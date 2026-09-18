package com.spectraledger.core.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/**
 * SHA-256 over a canonical, delimiter-separated representation of a ledger line plus the hash
 * of the line before it. This is what makes LedgerEntry rows a hash chain rather than a plain
 * table: changing any field of any past entry - even just balanceAfter on a row from hours ago
 * - changes that entry's own hash, which no longer matches what the NEXT entry recorded as its
 * previousEntryHash, and every entry after that is now provably inconsistent too.
 * AdminController#verifyChain recomputes this over the whole table and reports the first break.
 */
public final class LedgerHashUtil {

    private LedgerHashUtil() {
    }

    public static String hash(String previousHash, Object... fields) {
        StringBuilder canonical = new StringBuilder(previousHash);
        for (Object field : fields) {
            canonical.append('|').append(field);
        }
        return sha256Hex(canonical.toString());
    }

    private static String sha256Hex(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashBytes = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hashBytes);
        } catch (NoSuchAlgorithmException e) {
            // SHA-256 is guaranteed present on every standard JVM - this can't actually happen.
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }
}
