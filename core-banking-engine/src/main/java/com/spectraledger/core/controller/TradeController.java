package com.spectraledger.core.controller;

import com.spectraledger.core.dto.TradeResponse;
import com.spectraledger.core.repository.TradeRepository;
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
@RequestMapping("/api/trades")
@RequiredArgsConstructor
public class TradeController {

    private final TradeRepository tradeRepository;
    private final AccountService accountService;

    /** The market-wide trade tape (last 50) - deliberately not tenant-scoped, same as a real exchange's public tape. */
    @GetMapping
    public ResponseEntity<List<TradeResponse>> recentTrades() {
        List<TradeResponse> trades = tradeRepository.findTop50ByOrderByClearedAtDesc().stream()
                .map(TradeResponse::from)
                .toList();
        return ResponseEntity.ok(trades);
    }

    @GetMapping("/me")
    public ResponseEntity<List<TradeResponse>> myTrades(@AuthenticationPrincipal AuthenticatedTenant principal) {
        List<TradeResponse> trades = accountService.getTradeHistory(principal.tenantId()).stream()
                .map(TradeResponse::from)
                .toList();
        return ResponseEntity.ok(trades);
    }
}
