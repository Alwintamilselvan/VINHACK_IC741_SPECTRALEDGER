package com.spectraledger.core.exception;

import org.springframework.http.HttpStatus;

public class DuplicateUsernameException extends BankingException {
    public DuplicateUsernameException(String message) {
        super(HttpStatus.CONFLICT, message);
    }
}
