package com.spectraledger.core.exception;

import org.springframework.http.HttpStatus;

public class InvalidCredentialsException extends BankingException {
    public InvalidCredentialsException(String message) {
        super(HttpStatus.UNAUTHORIZED, message);
    }
}
