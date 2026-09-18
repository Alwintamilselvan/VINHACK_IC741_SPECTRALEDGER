package com.spectraledger.core.dto;

import com.spectraledger.core.domain.Order;
import com.spectraledger.core.domain.OrderSide;
import com.spectraledger.core.domain.OrderStatus;
import com.spectraledger.core.domain.QosTier;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record OrderResponse(
        Long id,
        UUID tenantId,
        UUID sliceId,
        OrderSide side,
        Integer quantityMbps,
        Integer remainingMbps,
        BigDecimal pricePerMbpsPerMin,
        Integer durationMinutes,
        QosTier qosTier,
        OrderStatus status,
        Instant createdAt,
        List<TradeResponse> immediateFills
) {
    public static OrderResponse from(Order o, List<TradeResponse> fills) {
        return new OrderResponse(
                o.getId(),
                o.getTenant().getId(),
                o.getSlice().getId(),
                o.getSide(),
                o.getQuantityMbps(),
                o.getRemainingMbps(),
                o.getPricePerMbpsPerMin(),
                o.getDurationMinutes(),
                o.getQosTier(),
                o.getStatus(),
                o.getCreatedAt(),
                fills
        );
    }
}
