package com.spectraledger.core.exception;

import org.springframework.http.HttpStatus;

/** Raised when an authenticated tenant tries to act on a resource (slice, order) it doesn't own. */
public class UnauthorizedTenantAccessException extends BankingException {
    public UnauthorizedTenantAccessException(String message) {
        super(HttpStatus.FORBIDDEN, message);
    }
}
