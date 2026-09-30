package com.meditest.patient;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PatientServiceTest {

    @Mock
    PatientRepository repo;

    @InjectMocks
    PatientService service;

    @Test
    void normalisesBloodType() {

        Patient p = new Patient();
        p.setName("Asha");
        p.setBloodType(" o+ ");

        when(repo.save(any()))
                .thenAnswer(inv -> inv.getArgument(0));

        assertEquals(
                "O+",
                service.create(p).getBloodType()
        );
    }
}