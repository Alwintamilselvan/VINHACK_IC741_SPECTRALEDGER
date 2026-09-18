package com.spectraledger.core.security;

import com.spectraledger.core.domain.Role;

import java.util.UUID;

/**
 * The JWT principal attached to every authenticated request by JwtAuthFilter. Controllers and
 * services read the tenant scope from THIS object - taken from the signed token - and never
 * from a tenantId supplied in a request body or query param. That is the entire RBAC story:
 * a tenant can only ever act as the identity its own token proves it holds.
 */
public record AuthenticatedTenant(UUID tenantId, String username, Role role) {
}
