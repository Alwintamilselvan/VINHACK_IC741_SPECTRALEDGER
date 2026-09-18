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
 * Singleton (always id = 1L) platform-wide risk controls, set by an ADMIN via
 * AdminSettingsController and enforced inside OrderService#submitOrder in the SAME locked
 * transaction as capacity reservation - not a UI-side suggestion the backend just trusts.
 *
 * safetyBufferPercent: fraction (0.10 = 10%) of every slice's total capacity that can never be
 * sold, regardless of how idle it looks to the forecasting engine - a guard against a bad
 * forecast selling capacity a tenant actually needs.
 *
 * price floors: the minimum price/Mbps/min an ASK may be listed at, per QoS tier - stops a
 * race-to-the-bottom / prevents an enterprise (or a buggy trading agent) from dumping capacity
 * for near-zero and crashing the market's price discovery.
 */
@Entity
@Table(name = "platform_settings")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PlatformSettings {

    @Id
    private Long id;

    @Column(nullable = false, precision = 5, scale = 4)
    private BigDecimal safetyBufferPercent;

    @Column(nullable = false, precision = 19, scale = 6)
    private BigDecimal priceFloorBronze;

    @Column(nullable = false, precision = 19, scale = 6)
    private BigDecimal priceFloorSilver;

    @Column(nullable = false, precision = 19, scale = 6)
    private BigDecimal priceFloorGold;

    @Column(nullable = false, precision = 19, scale = 6)
    private BigDecimal priceFloorPlatinum;

    @Column(nullable = false)
    private Instant updatedAt;

    public BigDecimal floorFor(QosTier tier) {
        return switch (tier) {
            case BRONZE -> priceFloorBronze;
            case SILVER -> priceFloorSilver;
            case GOLD -> priceFloorGold;
            case PLATINUM -> priceFloorPlatinum;
        };
    }

    public static PlatformSettings defaults() {
        return PlatformSettings.builder()
                .id(1L)
                .safetyBufferPercent(new BigDecimal("0.10"))
                .priceFloorBronze(BigDecimal.ZERO)
                .priceFloorSilver(BigDecimal.ZERO)
                .priceFloorGold(BigDecimal.ZERO)
                .priceFloorPlatinum(BigDecimal.ZERO)
                .updatedAt(Instant.now())
                .build();
    }
}
