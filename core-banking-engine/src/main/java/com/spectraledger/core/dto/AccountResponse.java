package com.spectraledger.core.dto;

import com.spectraledger.core.domain.Role;
import com.spectraledger.core.domain.Tenant;

import java.math.BigDecimal;
import java.util.UUID;

public record AccountResponse(
        UUID tenantId,
        String name,
        String username,
        Role role,
        BigDecimal balance,
        BigDecimal escrowBalance,
        BigDecimal totalEquity
) {
    /**
     * balance is already exclusive of escrow (funds move OUT of balance INTO escrowBalance the
     * moment a bid is placed - see OrderService#submitBid), so balance alone is what the tenant
     * can spend right now. totalEquity = balance + escrowBalance is included as a convenience
     * for the dashboard ("what am I worth including money tied up in open bids").
     */
    public static AccountResponse from(Tenant t) {
        return new AccountResponse(
                t.getId(),
                t.getName(),
                t.getUsername(),
                t.getRole(),
                t.getBalance(),
                t.getEscrowBalance(),
                t.getBalance().add(t.getEscrowBalance())
        );
    }
}
