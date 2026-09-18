package com.spectraledger.core.controller;

import com.spectraledger.core.dto.LedgerChainVerificationResponse;
import com.spectraledger.core.dto.PlatformSettingsRequest;
import com.spectraledger.core.dto.PlatformSettingsResponse;
import com.spectraledger.core.service.LedgerChainVerificationService;
import com.spectraledger.core.service.PlatformSettingsService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * Everything here is behind hasRole("ADMIN") (enforced in SecurityConfig at the URL level for
 * the whole /api/admin/** prefix) - an ENTERPRISE-role JWT gets a 403 before this controller
 * code ever runs.
 */
@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {

    private final PlatformSettingsService platformSettingsService;
    private final LedgerChainVerificationService ledgerChainVerificationService;

    @GetMapping("/settings")
    public ResponseEntity<PlatformSettingsResponse> getSettings() {
        return ResponseEntity.ok(PlatformSettingsResponse.from(platformSettingsService.get()));
    }

    /**
     * The frontend's "safety-buffer / price-floor" admin controls call this. Every ASK submitted
     * after this call is enforced against the new values inside the same locked transaction as
     * its capacity reservation - see OrderService#submitOrder.
     */
    @PutMapping("/settings")
    public ResponseEntity<PlatformSettingsResponse> updateSettings(@Valid @RequestBody PlatformSettingsRequest request) {
        return ResponseEntity.ok(PlatformSettingsResponse.from(platformSettingsService.update(request)));
    }

    /** Recomputes the ledger's hash chain from scratch and reports whether it's intact. */
    @GetMapping("/ledger/verify-chain")
    public ResponseEntity<LedgerChainVerificationResponse> verifyLedgerChain() {
        return ResponseEntity.ok(ledgerChainVerificationService.verify());
    }
}
