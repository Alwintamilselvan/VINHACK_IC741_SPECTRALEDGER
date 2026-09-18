package com.spectraledger.core.domain;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * One line of the double-entry ledger. amount is always stored positive; direction is carried
 * by entryType. Every Trade produces exactly two rows referencing the same trade, whose signed
 * deltas (+amount for CREDIT, -amount for DEBIT) sum to zero - that invariant is what makes this
 * a real double-entry ledger rather than just an activity log, and it is enforced by
 * construction in TradeSettlementService, never retrofitted after the fact.
 *
 * entryHash / previousEntryHash form a hash chain across the WHOLE table (every tenant, in
 * insertion order) - see LedgerHashUtil and TradeSettlementService. Tampering with any past
 * entry (even just editing balanceAfter in the database directly) changes that entry's hash and
 * breaks every link after it, which AdminController#verifyChain detects by recomputing the
 * chain from scratch.
 */
@Entity
@Table(name = "ledger_entries", indexes = {
        @Index(name = "idx_ledger_tenant", columnList = "tenant_id, created_at")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LedgerEntry {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "tenant_id", nullable = false)
    private Tenant tenant;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "trade_id", nullable = false)
    private Trade trade;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private EntryType entryType;

    @Column(nullable = false, precision = 19, scale = 4)
    private BigDecimal amount;

    /** Tenant's settled balance immediately after this entry was applied - an audit convenience, not the source of truth. */
    @Column(nullable = false, precision = 19, scale = 4)
    private BigDecimal balanceAfter;

    @Column(nullable = false, length = 255)
    private String description;

    @Column(nullable = false, updatable = false, length = 64)
    private String entryHash;

    @Column(nullable = false, updatable = false, length = 64)
    private String previousEntryHash;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    void onCreate() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
    }
}
