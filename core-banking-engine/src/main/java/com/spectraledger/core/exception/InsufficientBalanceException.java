package com.spectraledger.core.exception;

import org.springframework.http.HttpStatus;

public class InsufficientBalanceException extends BankingException {
    public InsufficientBalanceException(String message) {
        super(HttpStatus.CONFLICT, message);
    }
}
