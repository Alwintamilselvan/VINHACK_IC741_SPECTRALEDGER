package com.spectraledger.core.controller;

import com.spectraledger.core.dto.AccountResponse;
import com.spectraledger.core.dto.LedgerEntryResponse;
import com.spectraledger.core.dto.NetworkSliceResponse;
import com.spectraledger.core.security.AuthenticatedTenant;
import com.spectraledger.core.service.AccountService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/accounts")
@RequiredArgsConstructor
public class AccountController {

    private final AccountService accountService;

    @GetMapping("/me")
    public ResponseEntity<AccountResponse> me(@AuthenticationPrincipal AuthenticatedTenant principal) {
        return ResponseEntity.ok(AccountResponse.from(accountService.getTenant(principal.tenantId())));
    }

    @GetMapping("/me/ledger")
    public ResponseEntity<List<LedgerEntryResponse>> myLedger(@AuthenticationPrincipal AuthenticatedTenant principal) {
        List<LedgerEntryResponse> entries = accountService.getLedgerHistory(principal.tenantId()).stream()
                .map(LedgerEntryResponse::from)
                .toList();
        return ResponseEntity.ok(entries);
    }

    @GetMapping("/me/slices")
    public ResponseEntity<List<NetworkSliceResponse>> mySlices(@AuthenticationPrincipal AuthenticatedTenant principal) {
        List<NetworkSliceResponse> slices = accountService.getSlices(principal.tenantId()).stream()
                .map(NetworkSliceResponse::from)
                .toList();
        return ResponseEntity.ok(slices);
    }
}
