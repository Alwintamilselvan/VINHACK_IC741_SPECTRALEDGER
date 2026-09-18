package com.spectraledger.core.dto;

import com.spectraledger.core.domain.QosTier;
import com.spectraledger.core.domain.Trade;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record TradeResponse(
        Long id,
        Long bidOrderId,
        Long askOrderId,
        UUID buyerTenantId,
        UUID sellerTenantId,
        Integer quantityMbps,
        BigDecimal executionPrice,
        Integer durationMinutes,
        QosTier qosTier,
        BigDecimal totalAmount,
        String sliceReassignmentStatus,
        String sliceReassignmentRef,
        Instant clearedAt
) {
    public static TradeResponse from(Trade t) {
        return new TradeResponse(
                t.getId(),
                t.getBidOrder().getId(),
                t.getAskOrder().getId(),
                t.getBuyerTenant().getId(),
                t.getSellerTenant().getId(),
                t.getQuantityMbps(),
                t.getExecutionPrice(),
                t.getDurationMinutes(),
                t.getQosTier(),
                t.getTotalAmount(),
                t.getSliceReassignmentStatus().name(),
                t.getSliceReassignmentRef(),
                t.getClearedAt()
        );
    }
}
