package com.spectraledger.core.exception;

import org.springframework.http.HttpStatus;

public class PriceBelowFloorException extends BankingException {
    public PriceBelowFloorException(String message) {
        super(HttpStatus.CONFLICT, message);
    }
}
