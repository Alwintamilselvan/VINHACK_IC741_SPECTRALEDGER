package com.spectraledger.core.service;

import com.spectraledger.core.domain.*;
import com.spectraledger.core.event.TradeClearedEvent;
import com.spectraledger.core.exception.ResourceNotFoundException;
import com.spectraledger.core.repository.LedgerChainStateRepository;
import com.spectraledger.core.repository.LedgerEntryRepository;
import com.spectraledger.core.repository.OrderRepository;
import com.spectraledger.core.repository.TenantRepository;
import com.spectraledger.core.repository.TradeRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.UUID;

/**
 * The credibility centerpiece: this is the only place money moves between two tenants.
 *
 * ACID guarantee, concretely:
 *  - Atomicity    - everything below (both balance mutations, both order updates, the Trade
 *                   row, both LedgerEntry rows) is one @Transactional method. Postgres either
 *                   commits every write or none of them; a failure partway through rolls back
 *                   the whole thing, so a trade can never be "half applied".
 *  - Consistency  - the double-entry invariant (one DEBIT + one CREDIT of equal amount) is
 *                   enforced BEFORE the transaction commits (see the assertion below), and a
 *                   DB-level CHECK(balance >= 0) constraint (see Flyway/DDL) backstops it even
 *                   against an application bug.
 *  - Isolation    - both tenant rows are locked with SELECT ... FOR UPDATE
 *                   (PESSIMISTIC_WRITE, via TenantRepository#findByIdForUpdate) for the
 *                   duration of this transaction. No other transaction can read or write either
 *                   balance until this one commits or rolls back - that is what makes two
 *                   concurrent trades touching the same account impossible to interleave into a
 *                   corrupted balance. The two locks are always acquired in a fixed order
 *                   (ascending tenant UUID) regardless of who is buyer/seller, which is what
 *                   prevents two concurrent trades between the same pair of tenants from
 *                   deadlocking each other.
 *  - Durability   - once this method returns normally, Postgres's WAL has fsynced the commit;
 *                   it survives a crash immediately after.
 */
@Service
@RequiredArgsConstructor
public class TradeSettlementService {

    private static final Long CHAIN_STATE_ID = 1L;
    /** Matches the `precision = 19, scale = 4` declared on every money column (Tenant.balance/escrowBalance, LedgerEntry.amount/balanceAfter). */
    private static final int MONEY_SCALE = 4;

    private final TenantRepository tenantRepository;
    private final OrderRepository orderRepository;
    private final TradeRepository tradeRepository;
    private final LedgerEntryRepository ledgerEntryRepository;
    private final LedgerChainStateRepository ledgerChainStateRepository;
    private final ApplicationEventPublisher eventPublisher;

    @Transactional(propagation = Propagation.REQUIRES_NEW, isolation = Isolation.READ_COMMITTED)
    public Trade settle(Order bidOrder, Order askOrder, int matchedQty, BigDecimal executionPrice) {

        UUID buyerId = bidOrder.getTenant().getId();
        UUID sellerId = askOrder.getTenant().getId();

        // Canonical lock order: always the smaller UUID first. This is the deadlock-avoidance
        // rule - without it, thread A locking (buyer, seller) while thread B concurrently locks
        // (seller, buyer) for the reverse trade would eventually deadlock.
        UUID firstId = buyerId.compareTo(sellerId) <= 0 ? buyerId : sellerId;
        UUID secondId = buyerId.compareTo(sellerId) <= 0 ? sellerId : buyerId;

        Tenant firstLocked = tenantRepository.findByIdForUpdate(firstId)
                .orElseThrow(() -> new ResourceNotFoundException("Tenant not found: " + firstId));
        Tenant secondLocked = tenantRepository.findByIdForUpdate(secondId)
                .orElseThrow(() -> new ResourceNotFoundException("Tenant not found: " + secondId));

        Tenant buyer = firstLocked.getId().equals(buyerId) ? firstLocked : secondLocked;
        Tenant seller = firstLocked.getId().equals(sellerId) ? firstLocked : secondLocked;

        int durationMinutes = bidOrder.getDurationMinutes(); // bid & ask are always in the same bucket, so duration/qosTier match

        BigDecimal qty = BigDecimal.valueOf(matchedQty);
        BigDecimal duration = BigDecimal.valueOf(durationMinutes);

        // Every monetary figure that gets stored (ledger amount, balance, escrow) is rounded to
        // exactly the ledger/account columns' declared scale RIGHT HERE, before it's used for
        // anything - never left at whatever scale an intermediate multiplication happened to
        // produce. This matters for more than tidiness: the ledger hash chain (see below) hashes
        // these exact values, and if the in-memory value at hash time had a different scale than
        // what Postgres actually stores and later returns, GET /api/admin/ledger/verify-chain
        // would report a false tamper alarm on every single entry. Rounding once, consistently,
        // here, is what keeps "the value we hashed" and "the value in the database" identical.
        BigDecimal reservedForFill = bidOrder.getPricePerMbpsPerMin().multiply(qty).multiply(duration)
                .setScale(MONEY_SCALE, RoundingMode.HALF_UP);
        // What actually changes hands, at the resting order's (maker's) price.
        BigDecimal actualCost = executionPrice.multiply(qty).multiply(duration)
                .setScale(MONEY_SCALE, RoundingMode.HALF_UP);
        // Price improvement for the buyer, released back to spendable balance (not a ledger
        // transfer - no counterparty is involved, it's the buyer's own reservation shrinking).
        BigDecimal priceImprovementRefund = reservedForFill.subtract(actualCost);

        if (priceImprovementRefund.signum() < 0) {
            throw new IllegalStateException(
                    "Execution price " + executionPrice + " exceeds bid limit " + bidOrder.getPricePerMbpsPerMin()
                            + " - matching engine crossed an invalid pair, refusing to settle");
        }

        buyer.setEscrowBalance(buyer.getEscrowBalance().subtract(reservedForFill));
        buyer.setBalance(buyer.getBalance().add(priceImprovementRefund));
        seller.setBalance(seller.getBalance().add(actualCost));

        tenantRepository.save(buyer);
        tenantRepository.save(seller);

        bidOrder.setRemainingMbps(bidOrder.getRemainingMbps() - matchedQty);
        bidOrder.setReservedAmount(bidOrder.getReservedAmount().subtract(reservedForFill));
        bidOrder.setStatus(bidOrder.getRemainingMbps() == 0 ? OrderStatus.FILLED : OrderStatus.PARTIALLY_FILLED);

        askOrder.setRemainingMbps(askOrder.getRemainingMbps() - matchedQty);
        askOrder.setStatus(askOrder.getRemainingMbps() == 0 ? OrderStatus.FILLED : OrderStatus.PARTIALLY_FILLED);

        orderRepository.save(bidOrder);
        orderRepository.save(askOrder);

        Trade trade = Trade.builder()
                .bidOrder(bidOrder)
                .askOrder(askOrder)
                .buyerTenant(buyer)
                .sellerTenant(seller)
                .quantityMbps(matchedQty)
                .executionPrice(executionPrice)
                .durationMinutes(durationMinutes)
                .qosTier(bidOrder.getQosTier())
                .totalAmount(actualCost)
                .sliceReassignmentStatus(SliceReassignmentStatus.PENDING)
                .build();
        trade = tradeRepository.save(trade);

        LedgerEntry debit = LedgerEntry.builder()
                .tenant(buyer)
                .trade(trade)
                .entryType(EntryType.DEBIT)
                .amount(actualCost)
                .balanceAfter(buyer.getBalance())
                .description("Bandwidth lease payment - trade #" + trade.getId())
                .build();

        LedgerEntry credit = LedgerEntry.builder()
                .tenant(seller)
                .trade(trade)
                .entryType(EntryType.CREDIT)
                .amount(actualCost)
                .balanceAfter(seller.getBalance())
                .description("Bandwidth lease revenue - trade #" + trade.getId())
                .build();

        // The double-entry invariant, enforced by construction and checked defensively before
        // the transaction is allowed to commit: one debit, one credit, exactly equal amounts.
        if (debit.getAmount().compareTo(credit.getAmount()) != 0) {
            throw new IllegalStateException("Ledger invariant violated: debit " + debit.getAmount()
                    + " != credit " + credit.getAmount() + " for trade " + trade.getId());
        }

        // Extend the ledger's tamper-evident hash chain. Locking the singleton chain-state row
        // FIRST is what forces every trade in the system - regardless of which tenants or
        // buckets it involves - to append to the chain one at a time, so the chain can never
        // fork under concurrent settlement.
        LedgerChainState chain = ledgerChainStateRepository.findByIdForUpdate(CHAIN_STATE_ID)
                .orElseGet(() -> ledgerChainStateRepository.save(LedgerChainState.genesis()));

        debit.setPreviousEntryHash(chain.getLastEntryHash());
        debit.setEntryHash(LedgerHashUtil.hash(
                chain.getLastEntryHash(), buyer.getId(), trade.getId(), debit.getEntryType(),
                debit.getAmount(), debit.getBalanceAfter(), debit.getDescription()));

        credit.setPreviousEntryHash(debit.getEntryHash());
        credit.setEntryHash(LedgerHashUtil.hash(
                debit.getEntryHash(), seller.getId(), trade.getId(), credit.getEntryType(),
                credit.getAmount(), credit.getBalanceAfter(), credit.getDescription()));

        ledgerEntryRepository.save(debit);
        ledgerEntryRepository.save(credit);

        chain.setLastEntryHash(credit.getEntryHash());
        ledgerChainStateRepository.save(chain);

        // Published now, but only actually delivered to listeners after this transaction
        // commits (see MarketBroadcaster / SliceReassignmentService, both
        // @TransactionalEventListener(phase = AFTER_COMMIT)) - so nobody ever observes a trade
        // that later got rolled back.
        eventPublisher.publishEvent(new TradeClearedEvent(trade));

        return trade;
    }
}
