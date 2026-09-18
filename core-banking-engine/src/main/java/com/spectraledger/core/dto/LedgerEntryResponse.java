package com.spectraledger.core.dto;

import com.spectraledger.core.domain.LedgerEntry;

import java.math.BigDecimal;
import java.time.Instant;

public record LedgerEntryResponse(
        Long id,
        Long tradeId,
        String entryType,
        BigDecimal amount,
        BigDecimal balanceAfter,
        String description,
        String entryHash,
        String previousEntryHash,
        Instant createdAt
) {
    public static LedgerEntryResponse from(LedgerEntry e) {
        return new LedgerEntryResponse(
                e.getId(),
                e.getTrade().getId(),
                e.getEntryType().name(),
                e.getAmount(),
                e.getBalanceAfter(),
                e.getDescription(),
                e.getEntryHash(),
                e.getPreviousEntryHash(),
                e.getCreatedAt()
        );
    }
}
