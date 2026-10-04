package com.meditest.appointment;

import jakarta.validation.constraints.NotNull;

import java.time.LocalDateTime;

public record AppointmentRequest(
        @NotNull Long patientId,
        @NotNull LocalDateTime startsAt,
        String reason
) {}