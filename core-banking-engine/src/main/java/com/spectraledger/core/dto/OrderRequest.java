package com.spectraledger.core.dto;

import com.spectraledger.core.domain.OrderSide;
import com.spectraledger.core.domain.QosTier;
import jakarta.validation.constraints.*;

import java.math.BigDecimal;
import java.util.UUID;

/**
 * tenantId is deliberately NOT a field here - the submitting tenant is always taken from the
 * caller's JWT (see OrderController), so there is no way to submit an order on someone else's
 * behalf by editing the request body. This is also the shape the AI teammate's trading-agent
 * service calls: each agent authenticates as the tenant it represents and posts this body to
 * POST /api/orders.
 */
public record OrderRequest(
        @NotNull UUID sliceId,
        @NotNull OrderSide side,
        @NotNull @Min(1) Integer quantityMbps,
        @NotNull @DecimalMin(value = "0.0", inclusive = false) BigDecimal pricePerMbpsPerMin,
        @NotNull @Min(1) Integer durationMinutes,
        @NotNull QosTier qosTier
) {
}
