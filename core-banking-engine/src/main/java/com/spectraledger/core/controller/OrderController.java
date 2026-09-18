package com.spectraledger.core.controller;

import com.spectraledger.core.domain.Order;
import com.spectraledger.core.domain.QosTier;
import com.spectraledger.core.domain.Trade;
import com.spectraledger.core.dto.OrderBookBucketResponse;
import com.spectraledger.core.dto.OrderRequest;
import com.spectraledger.core.dto.OrderResponse;
import com.spectraledger.core.dto.TradeResponse;
import com.spectraledger.core.security.AuthenticatedTenant;
import com.spectraledger.core.service.MatchingEngineService;
import com.spectraledger.core.service.OrderService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;
    private final MatchingEngineService matchingEngineService;

    /**
     * The endpoint the AI teammate's trading-agent service calls to submit a bid or ask on
     * behalf of the enterprise it represents. Each agent authenticates with that enterprise's
     * own JWT - tenant scope always comes from the token, never from the request body.
     */
    @PostMapping
    public ResponseEntity<OrderResponse> submitOrder(
            @AuthenticationPrincipal AuthenticatedTenant principal,
            @Valid @RequestBody OrderRequest request) {

        Order order = orderService.submitOrder(principal.tenantId(), request);
        List<Trade> fills = orderService.match(order);
        List<TradeResponse> fillResponses = fills.stream().map(TradeResponse::from).toList();

        HttpStatus status = fills.isEmpty() ? HttpStatus.CREATED : HttpStatus.OK;
        return ResponseEntity.status(status).body(OrderResponse.from(order, fillResponses));
    }

    @DeleteMapping("/{orderId}")
    public ResponseEntity<OrderResponse> cancelOrder(
            @AuthenticationPrincipal AuthenticatedTenant principal,
            @PathVariable Long orderId) {
        Order cancelled = orderService.cancelOrder(principal.tenantId(), orderId);
        return ResponseEntity.ok(OrderResponse.from(cancelled, List.of()));
    }

    @GetMapping("/me")
    public ResponseEntity<List<OrderResponse>> myOrders(@AuthenticationPrincipal AuthenticatedTenant principal) {
        List<OrderResponse> orders = orderService.history(principal.tenantId()).stream()
                .map(o -> OrderResponse.from(o, List.of()))
                .toList();
        return ResponseEntity.ok(orders);
    }

    /** Full live order book across every active (qosTier, duration) bucket - what the market-terminal dashboard renders. */
    @GetMapping("/book")
    public ResponseEntity<List<OrderBookBucketResponse>> fullBook() {
        return ResponseEntity.ok(matchingEngineService.snapshotAll());
    }

    @GetMapping("/book/{qosTier}/{durationMinutes}")
    public ResponseEntity<OrderBookBucketResponse> bookBucket(
            @PathVariable QosTier qosTier,
            @PathVariable int durationMinutes) {
        return ResponseEntity.ok(matchingEngineService.snapshot(qosTier, durationMinutes));
    }
}
