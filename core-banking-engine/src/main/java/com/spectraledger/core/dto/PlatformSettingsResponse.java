package com.spectraledger.core.dto;

import com.spectraledger.core.domain.PlatformSettings;

import java.math.BigDecimal;
import java.time.Instant;

public record PlatformSettingsResponse(
        BigDecimal safetyBufferPercent,
        BigDecimal priceFloorBronze,
        BigDecimal priceFloorSilver,
        BigDecimal priceFloorGold,
        BigDecimal priceFloorPlatinum,
        Instant updatedAt
) {
    public static PlatformSettingsResponse from(PlatformSettings s) {
        return new PlatformSettingsResponse(
                s.getSafetyBufferPercent(),
                s.getPriceFloorBronze(),
                s.getPriceFloorSilver(),
                s.getPriceFloorGold(),
                s.getPriceFloorPlatinum(),
                s.getUpdatedAt());
    }
}
