package com.acme.billing;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import java.util.UUID;

@Entity
public class Invoice {
    @Id
    private UUID id;
    private String status;
}
