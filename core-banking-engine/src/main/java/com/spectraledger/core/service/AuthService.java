package com.spectraledger.core.service;

import com.spectraledger.core.domain.NetworkSlice;
import com.spectraledger.core.domain.Role;
import com.spectraledger.core.domain.Tenant;
import com.spectraledger.core.dto.AuthResponse;
import com.spectraledger.core.dto.LoginRequest;
import com.spectraledger.core.dto.RegisterTenantRequest;
import com.spectraledger.core.exception.DuplicateUsernameException;
import com.spectraledger.core.exception.InvalidCredentialsException;
import com.spectraledger.core.repository.NetworkSliceRepository;
import com.spectraledger.core.repository.TenantRepository;
import com.spectraledger.core.security.JwtService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final TenantRepository tenantRepository;
    private final NetworkSliceRepository sliceRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    @Transactional
    public AuthResponse register(RegisterTenantRequest req) {
        if (tenantRepository.existsByUsername(req.username())) {
            throw new DuplicateUsernameException("Username already taken: " + req.username());
        }

        Tenant tenant = Tenant.builder()
                .name(req.name())
                .username(req.username())
                .passwordHash(passwordEncoder.encode(req.password()))
                .role(Role.ENTERPRISE)
                .balance(req.openingBalance())
                .escrowBalance(BigDecimal.ZERO)
                .build();
        tenant = tenantRepository.save(tenant);

        NetworkSlice slice = NetworkSlice.builder()
                .tenant(tenant)
                .totalCapacityMbps(req.initialSliceCapacityMbps())
                .allocatedMbps(0)
                .qosTier(req.initialSliceQosTier())
                .build();
        sliceRepository.save(slice);

        String token = jwtService.issueToken(tenant.getId(), tenant.getUsername(), tenant.getRole());
        return new AuthResponse(token, tenant.getId(), tenant.getName(), tenant.getRole());
    }

    public AuthResponse login(LoginRequest req) {
        Tenant tenant = tenantRepository.findByUsername(req.username())
                .orElseThrow(() -> new InvalidCredentialsException("Invalid username or password"));

        if (!passwordEncoder.matches(req.password(), tenant.getPasswordHash())) {
            throw new InvalidCredentialsException("Invalid username or password");
        }

        String token = jwtService.issueToken(tenant.getId(), tenant.getUsername(), tenant.getRole());
        return new AuthResponse(token, tenant.getId(), tenant.getName(), tenant.getRole());
    }
}
