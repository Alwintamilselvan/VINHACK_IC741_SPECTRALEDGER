package com.spectraledger.core.service;

import com.spectraledger.core.domain.PlatformSettings;
import com.spectraledger.core.dto.PlatformSettingsRequest;
import com.spectraledger.core.repository.PlatformSettingsRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;

@Service
@RequiredArgsConstructor
public class PlatformSettingsService {

    private static final Long SETTINGS_ID = 1L;

    private final PlatformSettingsRepository repository;

    @Transactional(readOnly = true)
    public PlatformSettings get() {
        return repository.findById(SETTINGS_ID).orElseGet(PlatformSettings::defaults);
    }

    /**
     * Locks the settings row (creating it with defaults first if this is the very first write)
     * so a concurrent admin update can never interleave with an order submission that's reading
     * these values to decide whether to accept an ASK.
     */
    @Transactional
    public PlatformSettings update(PlatformSettingsRequest request) {
        PlatformSettings settings = repository.findByIdForUpdate(SETTINGS_ID)
                .orElseGet(() -> repository.save(PlatformSettings.defaults()));

        settings.setSafetyBufferPercent(request.safetyBufferPercent());
        settings.setPriceFloorBronze(request.priceFloorBronze());
        settings.setPriceFloorSilver(request.priceFloorSilver());
        settings.setPriceFloorGold(request.priceFloorGold());
        settings.setPriceFloorPlatinum(request.priceFloorPlatinum());
        settings.setUpdatedAt(Instant.now());

        return repository.save(settings);
    }

    /** Used by OrderService inside the same locked transaction as capacity reservation. */
    @Transactional(readOnly = true)
    public PlatformSettings getOrCreateDefault() {
        return repository.findById(SETTINGS_ID)
                .orElseGet(() -> repository.save(PlatformSettings.defaults()));
    }
}
