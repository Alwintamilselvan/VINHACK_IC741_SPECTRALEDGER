package com.spectraledger.core.exception;

import org.springframework.http.HttpStatus;

public class InsufficientCapacityException extends BankingException {
    public InsufficientCapacityException(String message) {
        super(HttpStatus.CONFLICT, message);
    }
}
