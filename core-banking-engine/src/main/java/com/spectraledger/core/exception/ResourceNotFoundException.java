package com.spectraledger.core.exception;

import org.springframework.http.HttpStatus;

public class ResourceNotFoundException extends BankingException {
    public ResourceNotFoundException(String message) {
        super(HttpStatus.NOT_FOUND, message);
    }
}
