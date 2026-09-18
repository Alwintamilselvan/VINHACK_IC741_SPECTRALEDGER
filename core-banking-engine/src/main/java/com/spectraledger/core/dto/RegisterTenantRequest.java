package com.spectraledger.core.dto;

import com.spectraledger.core.domain.QosTier;
import jakarta.validation.constraints.*;

import java.math.BigDecimal;

public record RegisterTenantRequest(
        @NotBlank @Size(max = 120) String name,
        @NotBlank @Size(min = 3, max = 60) String username,
        @NotBlank @Size(min = 6, max = 100) String password,
        @NotNull @DecimalMin(value = "0.0") BigDecimal openingBalance,
        @NotNull @Min(1) Integer initialSliceCapacityMbps,
        @NotNull QosTier initialSliceQosTier
) {
}
