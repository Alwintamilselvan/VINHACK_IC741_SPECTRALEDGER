package com.spectraledger.core.domain;

/**
 * ENTERPRISE: a tenant trading on the market - can only see/act on its own account, slices,
 * orders and ledger history.
 * ADMIN: platform operator - can view cross-tenant market data (order book, trade tape) and
 * adjust platform-wide safety settings. Never has direct access to move another tenant's money.
 */
public enum Role {
    ENTERPRISE,
    ADMIN
}
