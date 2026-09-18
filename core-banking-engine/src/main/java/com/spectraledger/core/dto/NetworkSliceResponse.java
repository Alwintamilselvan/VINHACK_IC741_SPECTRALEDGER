package com.spectraledger.core.dto;

import com.spectraledger.core.domain.NetworkSlice;
import com.spectraledger.core.domain.QosTier;

import java.util.UUID;

public record NetworkSliceResponse(
        UUID id,
        UUID tenantId,
        int totalCapacityMbps,
        int allocatedMbps,
        int availableMbps,
        QosTier qosTier
) {
    public static NetworkSliceResponse from(NetworkSlice s) {
        return new NetworkSliceResponse(
                s.getId(),
                s.getTenant().getId(),
                s.getTotalCapacityMbps(),
                s.getAllocatedMbps(),
                s.getAvailableMbps(),
                s.getQosTier()
        );
    }
}
