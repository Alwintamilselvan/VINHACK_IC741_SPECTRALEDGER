package com.spectraledger.core.domain;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;
import java.util.UUID;

/**
 * A tenant's dedicated 5G network slice. totalCapacityMbps is what the tenant pays their
 * telecom provider for. allocatedMbps is how much of that is currently committed - either to
 * the tenant's own live traffic, to capacity reserved behind an open ASK order, or to capacity
 * already leased out under an active trade. availableMbps (total - allocated) is what the
 * matching engine is allowed to sell on this tenant's behalf.
 */
@Entity
@Table(name = "network_slices")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class NetworkSlice {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "tenant_id", nullable = false)
    private Tenant tenant;

    @Column(nullable = false)
    private Integer totalCapacityMbps;

    @Column(nullable = false)
    private Integer allocatedMbps;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private QosTier qosTier;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    void onCreate() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
        if (allocatedMbps == null) {
            allocatedMbps = 0;
        }
    }

    @Transient
    public int getAvailableMbps() {
        return totalCapacityMbps - allocatedMbps;
    }
}
