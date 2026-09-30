package com.meditest.appointment;

import java.time.LocalDateTime;

public record AppointmentRequest(
        Long patientId,
        LocalDateTime startsAt,
        String reason
) {}