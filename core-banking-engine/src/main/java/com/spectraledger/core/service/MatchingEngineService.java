package com.spectraledger.core.service;

import com.spectraledger.core.domain.Order;
import com.spectraledger.core.domain.OrderSide;
import com.spectraledger.core.domain.OrderStatus;
import com.spectraledger.core.domain.QosTier;
import com.spectraledger.core.domain.Trade;
import com.spectraledger.core.dto.OrderBookBucketResponse;
import com.spectraledger.core.dto.OrderBookLevel;
import com.spectraledger.core.event.OrderBookChangedEvent;
import com.spectraledger.core.repository.OrderRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantLock;

/**
 * In-memory price-time-priority matching engine. Postgres remains the system of record (every
 * order is persisted the moment it's submitted, before this class ever sees it) - this class is
 * purely a fast, correctly-ordered INDEX over the currently-open orders, rebuilt from the
 * database on startup so a restart never loses book state.
 *
 * Orders are bucketed by (qosTier, durationMinutes): a bid only ever matches an ask that wants
 * the same QoS tier for the same lease duration, which is the platform's QoS/duration matching
 * constraint. Within a bucket, each side is a TreeMap keyed by price (bids sorted highest-first,
 * asks sorted lowest-first) whose values are FIFO queues - so "best price, then first-in" price-
 * time priority falls straight out of the data structure instead of needing a separate sort.
 *
 * Concurrency model: each bucket has its own ReentrantLock. All reads and mutations of a
 * bucket's book happen while holding that bucket's lock, so at most one thread is ever matching
 * orders in a given bucket at a time - there is no interleaving to reason about within a bucket.
 * Money movement itself is delegated to TradeSettlementService, whose own transaction takes the
 * real correctness burden (the DB-level tenant locks), so this class never needs to touch
 * balances directly.
 */
@Service
@RequiredArgsConstructor
public class MatchingEngineService {

    private final OrderRepository orderRepository;
    private final TradeSettlementService tradeSettlementService;
    private final ApplicationEventPublisher eventPublisher;

    private final Map<BucketKey, Bucket> buckets = new ConcurrentHashMap<>();

    private record BucketKey(QosTier qosTier, int durationMinutes) {
    }

    /** One matching bucket's resting order book. */
    private static final class Bucket {
        final ReentrantLock lock = new ReentrantLock();
        final TreeMap<BigDecimal, LinkedList<Order>> bids = new TreeMap<>(Comparator.reverseOrder());
        final TreeMap<BigDecimal, LinkedList<Order>> asks = new TreeMap<>();
    }

    @PostConstruct
    void rebuildFromDatabase() {
        List<Order> resting = orderRepository.findByStatusIn(
                List.of(OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED));
        // Sort by id ascending: id is IDENTITY-generated and therefore monotonically increasing
        // in insertion order, which is exactly the FIFO tiebreak this engine relies on.
        resting.sort(Comparator.comparing(Order::getId));
        for (Order order : resting) {
            insertResting(bucketFor(order.getQosTier(), order.getDurationMinutes()), order);
        }
    }

    private Bucket bucketFor(QosTier qosTier, int durationMinutes) {
        return buckets.computeIfAbsent(new BucketKey(qosTier, durationMinutes), k -> new Bucket());
    }

    private void insertResting(Bucket bucket, Order order) {
        TreeMap<BigDecimal, LinkedList<Order>> side = order.getSide() == OrderSide.BID ? bucket.bids : bucket.asks;
        side.computeIfAbsent(order.getPricePerMbpsPerMin(), k -> new LinkedList<>()).addLast(order);
    }

    /**
     * Attempts to cross {@code incoming} against the resting book. Returns every Trade produced
     * (zero, one, or many if the incoming order sweeps several price levels/orders). If quantity
     * remains after crossing everything it can, the remainder is inserted as a new resting order.
     * Must be called with {@code incoming} already durably persisted (OPEN status, full/partial
     * remaining quantity, funds or capacity already reserved) - see OrderService#submitOrder.
     */
    public List<Trade> processIncomingOrder(Order incoming) {
        Bucket bucket = bucketFor(incoming.getQosTier(), incoming.getDurationMinutes());
        List<Trade> trades = new ArrayList<>();

        bucket.lock.lock();
        try {
            TreeMap<BigDecimal, LinkedList<Order>> opposite =
                    incoming.getSide() == OrderSide.BID ? bucket.asks : bucket.bids;

            while (incoming.getRemainingMbps() > 0 && !opposite.isEmpty()) {
                Map.Entry<BigDecimal, LinkedList<Order>> bestLevel = opposite.firstEntry();
                BigDecimal bestPrice = bestLevel.getKey();

                boolean crosses = incoming.getSide() == OrderSide.BID
                        ? incoming.getPricePerMbpsPerMin().compareTo(bestPrice) >= 0
                        : incoming.getPricePerMbpsPerMin().compareTo(bestPrice) <= 0;
                if (!crosses) {
                    break;
                }

                LinkedList<Order> queue = bestLevel.getValue();
                Order resting = queue.peekFirst();
                int matchedQty = Math.min(incoming.getRemainingMbps(), resting.getRemainingMbps());

                Order bidOrder = incoming.getSide() == OrderSide.BID ? incoming : resting;
                Order askOrder = incoming.getSide() == OrderSide.BID ? resting : incoming;

                // Execution price is always the resting (maker) order's price - standard
                // price-time-priority convention, and what makes a limit order meaningful: the
                // taker never pays worse than their own limit, and may do better.
                Trade trade = tradeSettlementService.settle(bidOrder, askOrder, matchedQty, bestPrice);
                trades.add(trade);

                if (resting.getRemainingMbps() == 0) {
                    queue.pollFirst();
                    if (queue.isEmpty()) {
                        opposite.remove(bestPrice);
                    }
                }
            }

            if (incoming.getRemainingMbps() > 0) {
                insertResting(bucket, incoming);
            }
        } finally {
            bucket.lock.unlock();
        }

        eventPublisher.publishEvent(new OrderBookChangedEvent(incoming.getQosTier(), incoming.getDurationMinutes()));
        return trades;
    }

    /** Removes a resting order from the book, e.g. on cancellation. No-op if it isn't resting (already filled). */
    public void removeResting(Order order) {
        Bucket bucket = bucketFor(order.getQosTier(), order.getDurationMinutes());
        bucket.lock.lock();
        try {
            TreeMap<BigDecimal, LinkedList<Order>> side = order.getSide() == OrderSide.BID ? bucket.bids : bucket.asks;
            LinkedList<Order> queue = side.get(order.getPricePerMbpsPerMin());
            if (queue != null) {
                queue.removeIf(o -> o.getId().equals(order.getId()));
                if (queue.isEmpty()) {
                    side.remove(order.getPricePerMbpsPerMin());
                }
            }
        } finally {
            bucket.lock.unlock();
        }
        eventPublisher.publishEvent(new OrderBookChangedEvent(order.getQosTier(), order.getDurationMinutes()));
    }

    public OrderBookBucketResponse snapshot(QosTier qosTier, int durationMinutes) {
        Bucket bucket = buckets.get(new BucketKey(qosTier, durationMinutes));
        if (bucket == null) {
            return new OrderBookBucketResponse(qosTier, durationMinutes, List.of(), List.of());
        }
        bucket.lock.lock();
        try {
            return new OrderBookBucketResponse(
                    qosTier,
                    durationMinutes,
                    toLevels(bucket.bids),
                    toLevels(bucket.asks));
        } finally {
            bucket.lock.unlock();
        }
    }

    public List<OrderBookBucketResponse> snapshotAll() {
        return buckets.keySet().stream()
                .map(k -> snapshot(k.qosTier(), k.durationMinutes()))
                .filter(r -> !r.bids().isEmpty() || !r.asks().isEmpty())
                .toList();
    }

    private List<OrderBookLevel> toLevels(TreeMap<BigDecimal, LinkedList<Order>> side) {
        List<OrderBookLevel> levels = new ArrayList<>();
        for (Map.Entry<BigDecimal, LinkedList<Order>> entry : side.entrySet()) {
            int totalQty = entry.getValue().stream().mapToInt(Order::getRemainingMbps).sum();
            levels.add(new OrderBookLevel(entry.getKey(), totalQty, entry.getValue().size()));
        }
        return levels;
    }
}
