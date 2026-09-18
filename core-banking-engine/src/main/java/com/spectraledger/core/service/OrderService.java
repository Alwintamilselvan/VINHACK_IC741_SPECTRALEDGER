package com.spectraledger.core.service;

import com.spectraledger.core.domain.*;
import com.spectraledger.core.dto.OrderRequest;
import com.spectraledger.core.exception.InsufficientBalanceException;
import com.spectraledger.core.exception.InsufficientCapacityException;
import com.spectraledger.core.exception.PriceBelowFloorException;
import com.spectraledger.core.exception.ResourceNotFoundException;
import com.spectraledger.core.exception.UnauthorizedTenantAccessException;
import com.spectraledger.core.repository.NetworkSliceRepository;
import com.spectraledger.core.repository.OrderRepository;
import com.spectraledger.core.repository.TenantRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.UUID;

/**
 * Owns the reserve-then-persist step of an order's life: for a BID this escrows the full
 * potential cost out of spendable balance BEFORE the order can ever rest on the book, and for
 * an ASK it reserves the equivalent capacity on the tenant's slice. Both reservations happen
 * under the same pessimistic-lock discipline as trade settlement, which is what stops a tenant
 * from placing bids that add up to more than they can pay for even before any of them match -
 * the double-spend prevention starts here, not just at settlement time.
 *
 * Matching is deliberately NOT invoked from inside submitOrder's own @Transactional method
 * (see OrderController): calling it here would either run the whole matching sweep inside the
 * same transaction as the reservation (needlessly widening the lock window) or silently fail to
 * get its own transaction at all due to Spring's self-invocation proxy limitation. Keeping the
 * two steps as separate calls from the controller keeps the transaction boundaries exactly as
 * small as they need to be.
 */
@Service
@RequiredArgsConstructor
public class OrderService {

    private final OrderRepository orderRepository;
    private final TenantRepository tenantRepository;
    private final NetworkSliceRepository sliceRepository;
    private final MatchingEngineService matchingEngineService;
    private final PlatformSettingsService platformSettingsService;

    @Transactional
    public Order submitOrder(UUID tenantId, OrderRequest req) {
        NetworkSlice slice = sliceRepository.findById(req.sliceId())
                .orElseThrow(() -> new ResourceNotFoundException("Slice not found: " + req.sliceId()));

        if (!slice.getTenant().getId().equals(tenantId)) {
            throw new UnauthorizedTenantAccessException("Slice " + req.sliceId() + " does not belong to the authenticated tenant");
        }
        if (slice.getQosTier() != req.qosTier()) {
            throw new IllegalArgumentException("Order qosTier (" + req.qosTier() + ") must match the slice's qosTier (" + slice.getQosTier() + ")");
        }

        Order.OrderBuilder builder = Order.builder()
                .side(req.side())
                .quantityMbps(req.quantityMbps())
                .remainingMbps(req.quantityMbps())
                .pricePerMbpsPerMin(req.pricePerMbpsPerMin())
                .durationMinutes(req.durationMinutes())
                .qosTier(req.qosTier())
                .status(OrderStatus.OPEN);

        if (req.side() == OrderSide.BID) {
            Tenant tenant = tenantRepository.findByIdForUpdate(tenantId)
                    .orElseThrow(() -> new ResourceNotFoundException("Tenant not found: " + tenantId));

            // Rounded to the same scale as the balance/escrow columns (4) for the same reason
            // TradeSettlementService rounds its cost figures - keeps every monetary value that
            // ever gets stored at a single, consistent precision from the moment it's computed.
            BigDecimal reserved = req.pricePerMbpsPerMin()
                    .multiply(BigDecimal.valueOf(req.quantityMbps()))
                    .multiply(BigDecimal.valueOf(req.durationMinutes()))
                    .setScale(4, RoundingMode.HALF_UP);

            if (tenant.getBalance().compareTo(reserved) < 0) {
                throw new InsufficientBalanceException(
                        "Balance " + tenant.getBalance() + " is insufficient to reserve " + reserved + " for this bid");
            }

            tenant.setBalance(tenant.getBalance().subtract(reserved));
            tenant.setEscrowBalance(tenant.getEscrowBalance().add(reserved));
            tenantRepository.save(tenant);

            builder.tenant(tenant).slice(slice).reservedAmount(reserved);
        } else {
            PlatformSettings settings = platformSettingsService.getOrCreateDefault();

            BigDecimal floor = settings.floorFor(req.qosTier());
            if (req.pricePerMbpsPerMin().compareTo(floor) < 0) {
                throw new PriceBelowFloorException(
                        "Ask price " + req.pricePerMbpsPerMin() + " is below the admin-set price floor "
                                + floor + " for " + req.qosTier());
            }

            NetworkSlice lockedSlice = sliceRepository.findByIdForUpdate(slice.getId())
                    .orElseThrow(() -> new ResourceNotFoundException("Slice not found: " + slice.getId()));

            // The safety buffer holds back a fraction of total capacity from ever being sold,
            // regardless of how idle it looks - this is what an admin's "safety buffer %"
            // setting actually does, enforced here rather than trusted from the UI.
            int sellableCapacity = BigDecimal.valueOf(lockedSlice.getTotalCapacityMbps())
                    .multiply(BigDecimal.ONE.subtract(settings.getSafetyBufferPercent()))
                    .setScale(0, RoundingMode.FLOOR)
                    .intValue();
            int availableToSell = sellableCapacity - lockedSlice.getAllocatedMbps();

            if (availableToSell < req.quantityMbps()) {
                throw new InsufficientCapacityException(
                        "Only " + availableToSell + " Mbps available to sell on slice " + slice.getId()
                                + " (safety buffer reserves " + (lockedSlice.getTotalCapacityMbps() - sellableCapacity) + " Mbps)");
            }

            lockedSlice.setAllocatedMbps(lockedSlice.getAllocatedMbps() + req.quantityMbps());
            sliceRepository.save(lockedSlice);

            builder.tenant(lockedSlice.getTenant()).slice(lockedSlice).reservedAmount(BigDecimal.ZERO);
        }

        return orderRepository.save(builder.build());
    }

    /** Runs the matching sweep for a just-persisted order. See class javadoc for why this is a separate call. */
    public List<Trade> match(Order order) {
        return matchingEngineService.processIncomingOrder(order);
    }

    @Transactional
    public Order cancelOrder(UUID tenantId, Long orderId) {
        Order order = orderRepository.findByIdAndTenantId(orderId, tenantId)
                .orElseThrow(() -> new ResourceNotFoundException("Order not found: " + orderId));

        if (order.getStatus() == OrderStatus.FILLED || order.getStatus() == OrderStatus.CANCELLED) {
            throw new IllegalArgumentException("Order " + orderId + " is already " + order.getStatus() + " and cannot be cancelled");
        }

        matchingEngineService.removeResting(order);

        if (order.getSide() == OrderSide.BID) {
            Tenant tenant = tenantRepository.findByIdForUpdate(tenantId)
                    .orElseThrow(() -> new ResourceNotFoundException("Tenant not found: " + tenantId));
            BigDecimal releaseAmount = order.getReservedAmount();
            tenant.setEscrowBalance(tenant.getEscrowBalance().subtract(releaseAmount));
            tenant.setBalance(tenant.getBalance().add(releaseAmount));
            tenantRepository.save(tenant);
            order.setReservedAmount(BigDecimal.ZERO);
        } else {
            NetworkSlice slice = sliceRepository.findByIdForUpdate(order.getSlice().getId())
                    .orElseThrow(() -> new ResourceNotFoundException("Slice not found"));
            slice.setAllocatedMbps(slice.getAllocatedMbps() - order.getRemainingMbps());
            sliceRepository.save(slice);
        }

        order.setStatus(OrderStatus.CANCELLED);
        return orderRepository.save(order);
    }

    public List<Order> history(UUID tenantId) {
        return orderRepository.findByTenantIdOrderByCreatedAtDesc(tenantId);
    }
}
