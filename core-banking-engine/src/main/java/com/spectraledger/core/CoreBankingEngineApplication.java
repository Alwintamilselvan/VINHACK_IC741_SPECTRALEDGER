package com.spectraledger.core;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

import java.util.TimeZone;

@SpringBootApplication
@EnableAsync
public class CoreBankingEngineApplication {

    public static void main(String[] args) {
        // Force a canonical IANA timezone name before any datasource / Hikari / pgjdbc
        // connection is opened. On Windows, the JVM's default timezone can resolve to the
        // legacy alias "Asia/Calcutta" (from the OS "India Standard Time" mapping), which
        // recent PostgreSQL builds reject at connection time with:
        //   FATAL: invalid value for parameter "TimeZone": "Asia/Calcutta"
        // Setting this explicitly, in code, means the fix travels with the repo and works
        // identically for every teammate regardless of their machine's locale or how they
        // launch the app (VS Code, mvnw, IDE run configs, etc).
        TimeZone.setDefault(TimeZone.getTimeZone("Asia/Kolkata"));

        SpringApplication.run(CoreBankingEngineApplication.class, args);
    }
}
