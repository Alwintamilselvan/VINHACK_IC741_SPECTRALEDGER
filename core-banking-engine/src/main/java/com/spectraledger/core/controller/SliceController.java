package com.spectraledger.core.controller;

import com.spectraledger.core.domain.NetworkSlice;
import com.spectraledger.core.dto.CreateSliceRequest;
import com.spectraledger.core.dto.NetworkSliceResponse;
import com.spectraledger.core.repository.NetworkSliceRepository;
import com.spectraledger.core.repository.TenantRepository;
import com.spectraledger.core.exception.ResourceNotFoundException;
import com.spectraledger.core.security.AuthenticatedTenant;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/slices")
@RequiredArgsConstructor
public class SliceController {

    private final NetworkSliceRepository sliceRepository;
    private final TenantRepository tenantRepository;

    @PostMapping
    public ResponseEntity<NetworkSliceResponse> createSlice(
            @AuthenticationPrincipal AuthenticatedTenant principal,
            @Valid @RequestBody CreateSliceRequest request) {

        var tenant = tenantRepository.findById(principal.tenantId())
                .orElseThrow(() -> new ResourceNotFoundException("Tenant not found"));

        NetworkSlice slice = NetworkSlice.builder()
                .tenant(tenant)
                .totalCapacityMbps(request.totalCapacityMbps())
                .allocatedMbps(0)
                .qosTier(request.qosTier())
                .build();

        return ResponseEntity.status(HttpStatus.CREATED).body(NetworkSliceResponse.from(sliceRepository.save(slice)));
    }
}
