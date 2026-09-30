package com.meditest.record;

import jakarta.validation.constraints.*;

public record RecordRequest(
        @NotNull Long patientId,
        @NotBlank @Size(max = 10) String diagnosisCode,
        @Size(max = 2000) String notes
) {}