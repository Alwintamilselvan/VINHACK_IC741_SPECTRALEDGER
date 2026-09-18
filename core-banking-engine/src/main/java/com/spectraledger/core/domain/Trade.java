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
 * A single cleared match between a bid and an ask. One Trade always produces exactly two
 * LedgerEntry rows (one DEBIT, one CREDIT) written in the same database transaction - see
 * TradeSettlementService.
 */
@Entity
@Table(name = "trades")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Trade {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "bid_order_id", nullable = false)
    private Order bidOrder;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "ask_order_id", nullable = false)
    private Order askOrder;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "buyer_tenant_id", nullable = false)
    private Tenant buyerTenant;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "seller_tenant_id", nullable = false)
    private Tenant sellerTenant;

    @Column(nullable = false)
    private Integer quantityMbps;

    /** Execution price - always the resting (maker) order's price, per price-time priority convention. */
    @Column(nullable = false, precision = 19, scale = 6)
    private BigDecimal executionPrice;

    @Column(nullable = false)
    private Integer durationMinutes;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private QosTier qosTier;

    @Column(nullable = false, precision = 19, scale = 4)
    private BigDecimal totalAmount;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private SliceReassignmentStatus sliceReassignmentStatus;

    private String sliceReassignmentRef;

    @Column(nullable = false, updatable = false)
    private Instant clearedAt;

    @PrePersist
    void onCreate() {
        if (clearedAt == null) {
            clearedAt = Instant.now();
        }
        if (sliceReassignmentStatus == null) {
            sliceReassignmentStatus = SliceReassignmentStatus.PENDING;
        }
    }
}
