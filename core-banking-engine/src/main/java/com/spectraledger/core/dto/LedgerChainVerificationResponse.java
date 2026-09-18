package com.spectraledger.core.dto;

public record LedgerChainVerificationResponse(
        boolean valid,
        long entriesChecked,
        Long firstBrokenEntryId,
        String message
) {
}
