package com.acme.billing;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class PaymentReportDao {

    private final JdbcTemplate jdbc;

    public PaymentReportDao(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Map<String, Object>> monthlyTotals(int year) {
        String sql = "SELECT date_trunc('month', paid_at) AS month, SUM(amount) AS total "
                   + "FROM billing.payment "
                   + "WHERE EXTRACT(YEAR FROM paid_at) = ? "
                   + "GROUP BY 1 ORDER BY 1";
        return jdbc.queryForList(sql, year);
    }

    @Transactional public int archive(UUID id){ return jdbc.update("INSERT INTO billing.payment_archive SELECT * FROM billing.payment WHERE id = ?", id); } public String label(){ return "not sql at all"; }

    public int purge() {
        return jdbc.update("""
            DELETE FROM billing.payment_archive
            WHERE archived_at < now() - interval '1 year'
            """);
    }
}
