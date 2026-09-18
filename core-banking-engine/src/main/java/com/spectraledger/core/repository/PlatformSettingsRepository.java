package com.spectraledger.core.repository;

import com.spectraledger.core.domain.PlatformSettings;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface PlatformSettingsRepository extends JpaRepository<PlatformSettings, Long> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select s from PlatformSettings s where s.id = :id")
    Optional<PlatformSettings> findByIdForUpdate(@Param("id") Long id);
}
