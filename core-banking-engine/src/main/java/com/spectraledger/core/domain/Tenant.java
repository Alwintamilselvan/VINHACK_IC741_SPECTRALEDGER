package com.spectraledger.core.domain;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * An enterprise's account on the platform. This IS the tenant boundary: every Order,
 * NetworkSlice and LedgerEntry belongs to exactly one Tenant, and application-layer
 * authorization (see security package) guarantees a JWT for tenant A can never read or
 * mutate rows belonging to tenant B.
 *
 * balance      - settled, spendable funds.
 * escrowBalance - funds reserved against open BID orders. Reserved at order-submission time
 *                 (see OrderService#submitBid) so a tenant can never place bids that add up to
 *                 more than it can actually pay for, even before any of them match.
 */
@Entity
@Table(name = "tenants")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Tenant {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 120)
    private String name;

    @Column(nullable = false, unique = true, length = 60)
    private String username;

    @Column(nullable = false)
    private String passwordHash;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private Role role;

    @Column(nullable = false, precision = 19, scale = 4)
    private BigDecimal balance;

    @Column(nullable = false, precision = 19, scale = 4)
    private BigDecimal escrowBalance;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    void onCreate() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
        if (balance == null) {
            balance = BigDecimal.ZERO;
        }
        if (escrowBalance == null) {
            escrowBalance = BigDecimal.ZERO;
        }
    }
}
