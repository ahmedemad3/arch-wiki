package com.acme.messaging;

import org.apache.kafka.clients.producer.ProducerRecord;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class OutboxPublisher {

    private final KafkaTemplate<String, String> kafka;

    public OutboxPublisher(KafkaTemplate<String, String> kafka) {
        this.kafka = kafka;
    }

    public void relay(OutboxEvent event) {
        ProducerRecord<String, String> record = new ProducerRecord<>(event.topic(), event.key(), event.payload());
        kafka.send(record);
    }
}
