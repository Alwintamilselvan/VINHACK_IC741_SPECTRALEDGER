package com.spectraledger.core.websocket;

import com.spectraledger.core.dto.OrderBookBucketResponse;
import com.spectraledger.core.dto.TradeResponse;
import com.spectraledger.core.event.OrderBookChangedEvent;
import com.spectraledger.core.event.ReassignmentUpdatedEvent;
import com.spectraledger.core.event.TradeClearedEvent;
import com.spectraledger.core.service.MatchingEngineService;
import lombok.RequiredArgsConstructor;
import org.springframework.context.event.EventListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * The only thing standing between the domain events and the frontend. Nothing here touches the
 * database or a balance - it only reacts to events that other services publish, and pushes a
 * read-only view over STOMP. If this class were deleted entirely, the banking engine would
 * still be fully correct; the frontend would just have to poll REST instead of receiving live
 * pushes.
 *
 * OrderBookChangedEvent is published from MatchingEngineService OUTSIDE any database
 * transaction (the in-memory book mutation and its surrounding settlement transactions have
 * already finished by the time it fires), so it is handled with a plain @EventListener.
 * TradeClearedEvent and ReassignmentUpdatedEvent are published from INSIDE an active
 * @Transactional method, so they use @TransactionalEventListener(AFTER_COMMIT) - deliberately,
 * so the frontend is never shown a trade whose transaction went on to roll back.
 */
@Component
@RequiredArgsConstructor
public class MarketBroadcaster {

    private final SimpMessagingTemplate messagingTemplate;
    private final MatchingEngineService matchingEngineService;

    @EventListener
    public void onOrderBookChanged(OrderBookChangedEvent event) {
        OrderBookBucketResponse snapshot = matchingEngineService.snapshot(event.qosTier(), event.durationMinutes());
        messagingTemplate.convertAndSend("/topic/orderbook", snapshot);
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onTradeCleared(TradeClearedEvent event) {
        messagingTemplate.convertAndSend("/topic/trades", TradeResponse.from(event.trade()));
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onReassignmentUpdated(ReassignmentUpdatedEvent event) {
        messagingTemplate.convertAndSend("/topic/trades", TradeResponse.from(event.trade()));
    }
}
