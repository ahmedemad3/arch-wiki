package com.acme.messaging;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class InvoiceEventsListener {

    @KafkaListener(topics = {"billing.invoice.created", "billing.invoice.voided"}, groupId = "messaging")
    public void onInvoice(String payload) { }

    @KafkaListener(topics = "${acme.kafka.topics.payments}", groupId = "messaging")
    public void onPayment(String payload) { }
}
