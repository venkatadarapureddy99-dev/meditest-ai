package com.meditest.record;

import com.meditest.patient.Patient;
import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDate;

@Entity
@Table(name = "medical_records")
@Getter
@Setter
@NoArgsConstructor
public class MedicalRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(optional = false)
    private Patient patient;

    private String diagnosisCode;

    private String notes;

    private LocalDate recordedOn = LocalDate.now();
}