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
 * A resting bid or ask on the market. The numeric, DB-assigned {@code id} doubles as the
 * time-priority tiebreaker within a price level: IDENTITY generation guarantees it is
 * monotonically increasing in insertion order, so "lowest id first" at a given price is
 * exactly FIFO price-time priority without needing a separate sequence.
 */
@Entity
@Table(name = "orders", indexes = {
        // NOTE: columnList uses the PHYSICAL (snake_case) column names Hibernate's default
        // Spring Boot naming strategy generates from these Java field names, not the field
        // names themselves - qosTier -> qos_tier, durationMinutes -> duration_minutes.
        @Index(name = "idx_order_book_lookup", columnList = "qos_tier, duration_minutes, side, status")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "tenant_id", nullable = false)
    private Tenant tenant;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "slice_id", nullable = false)
    private NetworkSlice slice;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private OrderSide side;

    @Column(nullable = false)
    private Integer quantityMbps;

    @Column(nullable = false)
    private Integer remainingMbps;

    /** Price per Mbps per minute leased, in platform currency units. */
    @Column(nullable = false, precision = 19, scale = 6)
    private BigDecimal pricePerMbpsPerMin;

    @Column(nullable = false)
    private Integer durationMinutes;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private QosTier qosTier;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private OrderStatus status;

    /**
     * For BID orders only: the total (price * quantity * duration) reserved out of the
     * tenant's balance into escrow at submission time. Decremented as fills consume it;
     * whatever remains is released back to balance on cancellation.
     */
    @Column(precision = 19, scale = 4)
    private BigDecimal reservedAmount;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    void onCreate() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
        if (remainingMbps == null) {
            remainingMbps = quantityMbps;
        }
        if (status == null) {
            status = OrderStatus.OPEN;
        }
    }

    public BigDecimal totalCost(int quantity) {
        return pricePerMbpsPerMin
                .multiply(BigDecimal.valueOf(quantity))
                .multiply(BigDecimal.valueOf(durationMinutes));
    }
}
