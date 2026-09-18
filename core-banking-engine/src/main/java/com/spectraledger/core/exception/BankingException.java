package com.spectraledger.core.exception;

import org.springframework.http.HttpStatus;

/** Base type for every domain-level error the banking engine raises deliberately (as opposed to a bug). */
public class BankingException extends RuntimeException {

    private final HttpStatus status;

    public BankingException(HttpStatus status, String message) {
        super(message);
        this.status = status;
    }

    public HttpStatus getStatus() {
        return status;
    }
}
