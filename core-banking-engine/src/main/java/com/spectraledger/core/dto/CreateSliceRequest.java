package com.spectraledger.core.dto;

import com.spectraledger.core.domain.QosTier;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

public record CreateSliceRequest(
        @NotNull @Min(1) Integer totalCapacityMbps,
        @NotNull QosTier qosTier
) {
}
