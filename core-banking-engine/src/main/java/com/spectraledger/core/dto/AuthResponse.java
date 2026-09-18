package com.spectraledger.core.dto;

import com.spectraledger.core.domain.Role;

import java.util.UUID;

public record AuthResponse(
        String token,
        UUID tenantId,
        String name,
        Role role
) {
}
