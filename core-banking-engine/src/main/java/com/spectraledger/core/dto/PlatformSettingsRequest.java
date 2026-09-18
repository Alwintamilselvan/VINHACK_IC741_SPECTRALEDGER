package com.spectraledger.core.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;

public record PlatformSettingsRequest(
        @NotNull @DecimalMin("0.0") @DecimalMax("0.9") BigDecimal safetyBufferPercent,
        @NotNull @DecimalMin("0.0") BigDecimal priceFloorBronze,
        @NotNull @DecimalMin("0.0") BigDecimal priceFloorSilver,
        @NotNull @DecimalMin("0.0") BigDecimal priceFloorGold,
        @NotNull @DecimalMin("0.0") BigDecimal priceFloorPlatinum
) {
}
