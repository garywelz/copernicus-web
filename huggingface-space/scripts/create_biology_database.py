#!/usr/bin/env python3
"""
Create Biology Processes Database
Generates JSON files and HTML viewers for higher-level biological processes
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Biology process definitions with categories and basic flowchart templates
BIOLOGY_PROCESSES = {
    "reproduction_development": {
        "name": "Reproduction & Development",
        "processes": [
            {
                "name": "Mating Behavior Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A1[Environmental Cues] --> B1[Reproductive Readiness Assessment]
    C1[Mate Availability] --> D1[Signaling & Display]
    B1 --> E1[Courtship Initiation]
    D1 --> E1
    E1 --> F1[Behavioral Response]
    F1 --> G1{Mate Acceptance?}
    G1 -->|Yes| H1[Copulation]
    G1 -->|No| I1[Rejection Response]
    H1 --> J1[Reproductive Success]
    I1 --> K1[Search for Alternative]
    
    style A1 fill:#ff6b6b,color:#fff
    style C1 fill:#ff6b6b,color:#fff
    style B1 fill:#ffd43b,color:#000
    style D1 fill:#ffd43b,color:#000
    style E1 fill:#51cf66,color:#fff
    style F1 fill:#51cf66,color:#fff
    style G1 fill:#74c0fc,color:#fff
    style H1 fill:#51cf66,color:#fff
    style I1 fill:#74c0fc,color:#fff
    style J1 fill:#b197fc,color:#fff
    style K1 fill:#74c0fc,color:#fff"""
            },
            {
                "name": "Fertilization Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A2[Sperm Release] --> B2[Sperm Migration]
    C2[Ovum Maturation] --> D2[Ovulation]
    B2 --> E2[Zona Pellucida Binding]
    D2 --> E2
    E2 --> F2[Acrosome Reaction]
    F2 --> G2[Enzyme Release]
    G2 --> H2[Zona Penetration]
    H2 --> I2[Membrane Fusion]
    I2 --> J2[Cortical Reaction]
    J2 --> K2[Polyspermy Block]
    K2 --> L2[Pronuclei Formation]
    L2 --> M2[Zygote Formation]
    
    style A2 fill:#ff6b6b,color:#fff
    style C2 fill:#ff6b6b,color:#fff
    style B2 fill:#ffd43b,color:#000
    style D2 fill:#ffd43b,color:#000
    style E2 fill:#51cf66,color:#fff
    style F2 fill:#51cf66,color:#fff
    style G2 fill:#51cf66,color:#fff
    style H2 fill:#74c0fc,color:#fff
    style I2 fill:#74c0fc,color:#fff
    style J2 fill:#51cf66,color:#fff
    style K2 fill:#74c0fc,color:#fff
    style L2 fill:#74c0fc,color:#fff
    style M2 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Pollination Process",
                "organism": "Plants",
                "mermaid": """graph TD
    A3[Pollen Development] --> B3[Anther Dehiscence]
    C3[Pollinator Activity] --> D3[Pollen Transfer]
    B3 --> D3
    D3 --> E3[Stigma Reception]
    E3 --> F3[Pollen Adhesion]
    F3 --> G3[Hydration]
    G3 --> H3[Germination]
    H3 --> I3[Pollen Tube Growth]
    I3 --> J3[Style Navigation]
    J3 --> K3[Ovary Entry]
    K3 --> L3[Double Fertilization]
    
    style A3 fill:#ff6b6b,color:#fff
    style C3 fill:#ff6b6b,color:#fff
    style B3 fill:#ffd43b,color:#000
    style D3 fill:#ffd43b,color:#000
    style E3 fill:#51cf66,color:#fff
    style F3 fill:#51cf66,color:#fff
    style G3 fill:#74c0fc,color:#fff
    style H3 fill:#74c0fc,color:#fff
    style I3 fill:#51cf66,color:#fff
    style J3 fill:#51cf66,color:#fff
    style K3 fill:#74c0fc,color:#fff
    style L3 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Embryonic Development Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A4[Fertilized Egg] --> B4[Cleavage Divisions]
    B4 --> C4[Morula Formation]
    C4 --> D4[Blastula Formation]
    D4 --> E4[Gastrulation]
    E4 --> F4[Germ Layer Formation]
    F4 --> G4[Ectoderm]
    F4 --> H4[Mesoderm]
    F4 --> I4[Endoderm]
    G4 --> J4[Organogenesis]
    H4 --> J4
    I4 --> J4
    J4 --> K4[Neurulation]
    K4 --> L4[Limb Bud Formation]
    L4 --> M4[Organ Maturation]
    M4 --> N4[Fetal Development]
    
    style A4 fill:#ff6b6b,color:#fff
    style B4 fill:#ffd43b,color:#000
    style C4 fill:#ffd43b,color:#000
    style D4 fill:#ffd43b,color:#000
    style E4 fill:#51cf66,color:#fff
    style F4 fill:#51cf66,color:#fff
    style G4 fill:#74c0fc,color:#fff
    style H4 fill:#74c0fc,color:#fff
    style I4 fill:#74c0fc,color:#fff
    style J4 fill:#51cf66,color:#fff
    style K4 fill:#51cf66,color:#fff
    style L4 fill:#74c0fc,color:#fff
    style M4 fill:#74c0fc,color:#fff
    style N4 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Metamorphosis Process",
                "organism": "Amphibians/Insects",
                "mermaid": """graph TD
    A5[Larval Stage] --> B5[Environmental Trigger]
    B5 --> C5[Hormonal Cascade]
    C5 --> D5[Cell Death Initiation]
    C5 --> E5[Cell Proliferation]
    D5 --> F5[Tissue Remodeling]
    E5 --> F5
    F5 --> G5[Organ Transformation]
    G5 --> H5[Limbs Development]
    H5 --> I5[Adult Features]
    I5 --> J5[Metamorphosis Complete]
    J5 --> K5[Adult Stage]
    
    style A5 fill:#ff6b6b,color:#fff
    style B5 fill:#ff6b6b,color:#fff
    style C5 fill:#ffd43b,color:#000
    style D5 fill:#51cf66,color:#fff
    style E5 fill:#51cf66,color:#fff
    style F5 fill:#51cf66,color:#fff
    style G5 fill:#74c0fc,color:#fff
    style H5 fill:#74c0fc,color:#fff
    style I5 fill:#74c0fc,color:#fff
    style J5 fill:#b197fc,color:#fff
    style K5 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Seed Germination Process",
                "organism": "Plants",
                "mermaid": """graph TD
    A6[Mature Seed] --> B6[Dormancy State]
    C6[Environmental Signals] --> D6[Water Uptake]
    C6 --> E6[Temperature Cues]
    C6 --> F6[Light Exposure]
    D6 --> G6[Imbibition]
    E6 --> G6
    F6 --> G6
    G6 --> H6[Enzyme Activation]
    H6 --> I6[Reserve Mobilization]
    I6 --> J6[Radicle Emergence]
    J6 --> K6[Root Development]
    K6 --> L6[Cotyledon Expansion]
    L6 --> M6[Seedling Establishment]
    
    style A6 fill:#ff6b6b,color:#fff
    style C6 fill:#ff6b6b,color:#fff
    style B6 fill:#ffd43b,color:#000
    style D6 fill:#ffd43b,color:#000
    style E6 fill:#ffd43b,color:#000
    style F6 fill:#ffd43b,color:#000
    style G6 fill:#51cf66,color:#fff
    style H6 fill:#51cf66,color:#fff
    style I6 fill:#51cf66,color:#fff
    style J6 fill:#74c0fc,color:#fff
    style K6 fill:#74c0fc,color:#fff
    style L6 fill:#74c0fc,color:#fff
    style M6 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Flowering Process",
                "organism": "Plants",
                "mermaid": """graph TD
    A7[Vegetative Growth] --> B7[Floral Induction Signals]
    C7[Photoperiod] --> D7[Vernalization]
    C7 --> E7[Hormonal Cues]
    B7 --> F7[Floral Meristem Initiation]
    D7 --> F7
    E7 --> F7
    F7 --> G7[Organ Identity Genes]
    G7 --> H7[Sepal Formation]
    G7 --> I7[Petal Formation]
    G7 --> J7[Stamen Formation]
    G7 --> K7[Carpel Formation]
    H7 --> L7[Flower Development]
    I7 --> L7
    J7 --> L7
    K7 --> L7
    L7 --> M7[Anthesis]
    
    style A7 fill:#ff6b6b,color:#fff
    style C7 fill:#ff6b6b,color:#fff
    style B7 fill:#ffd43b,color:#000
    style D7 fill:#ffd43b,color:#000
    style E7 fill:#ffd43b,color:#000
    style F7 fill:#51cf66,color:#fff
    style G7 fill:#51cf66,color:#fff
    style H7 fill:#74c0fc,color:#fff
    style I7 fill:#74c0fc,color:#fff
    style J7 fill:#74c0fc,color:#fff
    style K7 fill:#74c0fc,color:#fff
    style L7 fill:#51cf66,color:#fff
    style M7 fill:#b197fc,color:#fff"""
            }
        ]
    },
    "growth_morphogenesis": {
        "name": "Growth & Morphogenesis",
        "processes": [
            {
                "name": "Tissue Regeneration Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A8[Wound Detection] --> B8[Inflammatory Response]
    B8 --> C8[Cell Migration]
    C8 --> D8[Stem Cell Activation]
    D8 --> E8[Cell Proliferation]
    E8 --> F8[Differentiation]
    F8 --> G8[Tissue Replacement]
    G8 --> H8[Remodeling]
    H8 --> I8[Function Restoration]
    
    style A8 fill:#ff6b6b,color:#fff
    style B8 fill:#ffd43b,color:#000
    style C8 fill:#51cf66,color:#fff
    style D8 fill:#51cf66,color:#fff
    style E8 fill:#51cf66,color:#fff
    style F8 fill:#74c0fc,color:#fff
    style G8 fill:#74c0fc,color:#fff
    style H8 fill:#51cf66,color:#fff
    style I8 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Apical Meristem Development",
                "organism": "Plants",
                "mermaid": """graph TD
    A9[Embryonic Meristem] --> B9[Cell Division Zone]
    B9 --> C9[Cell Elongation Zone]
    C9 --> D9[Cell Differentiation Zone]
    D9 --> E9[Leaf Primordia]
    D9 --> F9[Stem Tissue]
    D9 --> G9[Vascular Tissue]
    E9 --> H9[Organ Formation]
    F9 --> H9
    G9 --> H9
    H9 --> I9[Growth Continuation]
    
    style A9 fill:#ff6b6b,color:#fff
    style B9 fill:#ffd43b,color:#000
    style C9 fill:#ffd43b,color:#000
    style D9 fill:#51cf66,color:#fff
    style E9 fill:#74c0fc,color:#fff
    style F9 fill:#74c0fc,color:#fff
    style G9 fill:#74c0fc,color:#fff
    style H9 fill:#51cf66,color:#fff
    style I9 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Molting Process",
                "organism": "Arthropods",
                "mermaid": """graph TD
    A10[Growth Signal] --> B10[Ecdysone Production]
    B10 --> C10[Apolysis Initiation]
    C10 --> D10[New Cuticle Secretion]
    D10 --> E10[Enzyme Production]
    E10 --> F10[Old Cuticle Digestion]
    F10 --> G10[Water Absorption]
    G10 --> H10[Cuticle Shedding]
    H10 --> I10[Sclerotization]
    I10 --> J10[New Exoskeleton]
    
    style A10 fill:#ff6b6b,color:#fff
    style B10 fill:#ffd43b,color:#000
    style C10 fill:#51cf66,color:#fff
    style D10 fill:#51cf66,color:#fff
    style E10 fill:#51cf66,color:#fff
    style F10 fill:#51cf66,color:#fff
    style G10 fill:#74c0fc,color:#fff
    style H10 fill:#51cf66,color:#fff
    style I10 fill:#74c0fc,color:#fff
    style J10 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Skeletal Growth Process",
                "organism": "Vertebrates",
                "mermaid": """graph TD
    A11[Cartilage Template] --> B11[Chondrocyte Proliferation]
    B11 --> C11[Ossification Center]
    C11 --> D11[Osteoblast Differentiation]
    D11 --> E11[Bone Matrix Deposition]
    E11 --> F11[Mineralization]
    F11 --> G11[Bone Remodeling]
    G11 --> H11[Growth Plate Activity]
    H11 --> I11[Longitudinal Growth]
    
    style A11 fill:#ff6b6b,color:#fff
    style B11 fill:#ffd43b,color:#000
    style C11 fill:#ffd43b,color:#000
    style D11 fill:#51cf66,color:#fff
    style E11 fill:#51cf66,color:#fff
    style F11 fill:#74c0fc,color:#fff
    style G11 fill:#51cf66,color:#fff
    style H11 fill:#74c0fc,color:#fff
    style I11 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Branching Morphogenesis",
                "organism": "Plants/Animals",
                "mermaid": """graph TD
    A12[Primary Structure] --> B12[Branching Signal]
    B12 --> C12[Pattern Formation]
    C12 --> D12[Tip Growth]
    D12 --> E12{Lateral Inhibition?}
    E12 -->|Yes| F12[Branch Suppression]
    E12 -->|No| G12[Branch Initiation]
    F12 --> H12[Pattern Maintenance]
    G12 --> I12[Secondary Branching]
    H12 --> J12[Final Architecture]
    I12 --> J12
    
    style A12 fill:#ff6b6b,color:#fff
    style B12 fill:#ff6b6b,color:#fff
    style C12 fill:#ffd43b,color:#000
    style D12 fill:#51cf66,color:#fff
    style E12 fill:#74c0fc,color:#fff
    style F12 fill:#51cf66,color:#fff
    style G12 fill:#51cf66,color:#fff
    style H12 fill:#74c0fc,color:#fff
    style I12 fill:#74c0fc,color:#fff
    style J12 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Leaf Development Process",
                "organism": "Plants",
                "mermaid": """graph TD
    A13[Shoot Apical Meristem] --> B13[Leaf Primordium Initiation]
    B13 --> C13[Adaxial-Abaxial Patterning]
    C13 --> D13[Lamina Outgrowth]
    D13 --> E13[Vein Formation]
    E13 --> F13[Cell Expansion]
    F13 --> G13[Differentiation]
    G13 --> H13[Mature Leaf]
    H13 --> I13[Senescence]
    
    style A13 fill:#ff6b6b,color:#fff
    style B13 fill:#ffd43b,color:#000
    style C13 fill:#51cf66,color:#fff
    style D13 fill:#51cf66,color:#fff
    style E13 fill:#74c0fc,color:#fff
    style F13 fill:#74c0fc,color:#fff
    style G13 fill:#51cf66,color:#fff
    style H13 fill:#b197fc,color:#fff
    style I13 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Limbs Formation Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A14[Lateral Plate Mesoderm] --> B14[Limb Field Specification]
    B14 --> C14[Limb Bud Formation]
    C14 --> D14[Apical Ectodermal Ridge]
    D14 --> E14[Proliferation Zone]
    E14 --> F14[Proximo-Distal Patterning]
    F14 --> G14[Antero-Posterior Patterning]
    G14 --> H14[Digit Formation]
    H14 --> I14[Interdigital Apoptosis]
    I14 --> J14[Final Limb Structure]
    
    style A14 fill:#ff6b6b,color:#fff
    style B14 fill:#ffd43b,color:#000
    style C14 fill:#ffd43b,color:#000
    style D14 fill:#51cf66,color:#fff
    style E14 fill:#51cf66,color:#fff
    style F14 fill:#51cf66,color:#fff
    style G14 fill:#51cf66,color:#fff
    style H14 fill:#74c0fc,color:#fff
    style I14 fill:#51cf66,color:#fff
    style J14 fill:#b197fc,color:#fff"""
            }
        ]
    },
    "behavior_communication": {
        "name": "Behavior & Communication",
        "processes": [
            {
                "name": "Migration Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A15[Seasonal Cues] --> B15[Orientation Mechanism]
    C15[Internal Compass] --> D15[Navigation System]
    B15 --> E15[Direction Selection]
    D15 --> E15
    E15 --> F15[Path Following]
    F15 --> G15[Energy Management]
    G15 --> H15[Stopover Behavior]
    H15 --> I15[Destination Arrival]
    
    style A15 fill:#ff6b6b,color:#fff
    style C15 fill:#ff6b6b,color:#fff
    style B15 fill:#ffd43b,color:#000
    style D15 fill:#ffd43b,color:#000
    style E15 fill:#51cf66,color:#fff
    style F15 fill:#51cf66,color:#fff
    style G15 fill:#74c0fc,color:#fff
    style H15 fill:#74c0fc,color:#fff
    style I15 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Hibernation Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A16[Environmental Change] --> B16[Metabolic Preparation]
    B16 --> C16[Fat Accumulation]
    C16 --> D16[Body Temperature Drop]
    D16 --> E16[Heart Rate Reduction]
    E16 --> F16[Breathing Slowed]
    F16 --> G16[Metabolic Suppression]
    G16 --> H16[Hibernation State]
    H16 --> I16[Periodic Arousal]
    I16 --> J16[Spring Emergence]
    
    style A16 fill:#ff6b6b,color:#fff
    style B16 fill:#ffd43b,color:#000
    style C16 fill:#ffd43b,color:#000
    style D16 fill:#51cf66,color:#fff
    style E16 fill:#51cf66,color:#fff
    style F16 fill:#51cf66,color:#fff
    style G16 fill:#74c0fc,color:#fff
    style H16 fill:#74c0fc,color:#fff
    style I16 fill:#74c0fc,color:#fff
    style J16 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Foraging Behavior Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A17[Food Deprivation] --> B17[Search Initiation]
    B17 --> C17[Resource Detection]
    C17 --> D17[Quality Assessment]
    D17 --> E17{Profitable?}
    E17 -->|Yes| F17[Capture Attempt]
    E17 -->|No| G17[Continue Search]
    F17 --> H17[Handling]
    H17 --> I17[Consumption]
    G17 --> C17
    I17 --> J17[Energy Gain]
    
    style A17 fill:#ff6b6b,color:#fff
    style B17 fill:#ffd43b,color:#000
    style C17 fill:#51cf66,color:#fff
    style D17 fill:#51cf66,color:#fff
    style E17 fill:#74c0fc,color:#fff
    style F17 fill:#51cf66,color:#fff
    style G17 fill:#74c0fc,color:#fff
    style H17 fill:#51cf66,color:#fff
    style I17 fill:#51cf66,color:#fff
    style J17 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Social Hierarchy Establishment",
                "organism": "Animals",
                "mermaid": """graph TD
    A18[Group Formation] --> B18[Individual Assessment]
    B18 --> C18[Agonistic Encounters]
    C18 --> D18[Competition]
    D18 --> E18[Victory/Defeat]
    E18 --> F18[Rank Assignment]
    F18 --> G18[Hierarchy Structure]
    G18 --> H18[Stabilization]
    H18 --> I18[Resource Access Rules]
    
    style A18 fill:#ff6b6b,color:#fff
    style B18 fill:#ffd43b,color:#000
    style C18 fill:#51cf66,color:#fff
    style D18 fill:#51cf66,color:#fff
    style E18 fill:#74c0fc,color:#fff
    style F18 fill:#74c0fc,color:#fff
    style G18 fill:#b197fc,color:#fff
    style H18 fill:#b197fc,color:#fff
    style I18 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Communication Signal Production",
                "organism": "Animals",
                "mermaid": """graph TD
    A19[Information Source] --> B19[Signal Encoding]
    B19 --> C19[Signal Modality Selection]
    C19 --> D19[Vocal Production]
    C19 --> E19[Chemical Release]
    C19 --> F19[Visual Display]
    D19 --> G19[Signal Transmission]
    E19 --> G19
    F19 --> G19
    G19 --> H19[Receptor Detection]
    H19 --> I19[Response Elicitation]
    
    style A19 fill:#ff6b6b,color:#fff
    style B19 fill:#ffd43b,color:#000
    style C19 fill:#51cf66,color:#fff
    style D19 fill:#74c0fc,color:#fff
    style E19 fill:#74c0fc,color:#fff
    style F19 fill:#74c0fc,color:#fff
    style G19 fill:#51cf66,color:#fff
    style H19 fill:#74c0fc,color:#fff
    style I19 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Nest Building Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A20[Reproductive Season] --> B20[Site Selection]
    B20 --> C20[Material Collection]
    C20 --> D20[Construction Initiation]
    D20 --> E20[Structure Assembly]
    E20 --> F20[Shape Formation]
    F20 --> G20[Lining Addition]
    G20 --> H20[Completion]
    H20 --> I20[Nest Maintenance]
    
    style A20 fill:#ff6b6b,color:#fff
    style B20 fill:#ffd43b,color:#000
    style C20 fill:#51cf66,color:#fff
    style D20 fill:#51cf66,color:#fff
    style E20 fill:#51cf66,color:#fff
    style F20 fill:#74c0fc,color:#fff
    style G20 fill:#74c0fc,color:#fff
    style H20 fill:#b197fc,color:#fff
    style I20 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Parental Care Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A21[Offspring Birth] --> B21[Recognition]
    B21 --> C21[Protection Initiation]
    C21 --> D21[Thermoregulation]
    D21 --> E21[Feeding]
    E21 --> F21[Grooming]
    F21 --> G21[Teaching Behaviors]
    G21 --> H21[Independence Training]
    H21 --> I21[Weaning]
    
    style A21 fill:#ff6b6b,color:#fff
    style B21 fill:#ffd43b,color:#000
    style C21 fill:#51cf66,color:#fff
    style D21 fill:#51cf66,color:#fff
    style E21 fill:#51cf66,color:#fff
    style F21 fill:#51cf66,color:#fff
    style G21 fill:#74c0fc,color:#fff
    style H21 fill:#74c0fc,color:#fff
    style I21 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Symbiotic Relationship Formation",
                "organism": "Multiple",
                "mermaid": """graph TD
    A22[Host Organism] --> B22[Symbiont Encounter]
    C22[Symbiont Organism] --> B22
    B22 --> D22[Recognition]
    D22 --> E22{Compatible?}
    E22 -->|Yes| F22[Association Establishment]
    E22 -->|No| G22[Rejection]
    F22 --> H22[Benefits Exchange]
    H22 --> I22[Relationship Maintenance]
    G22 --> J22[Separate Existence]
    
    style A22 fill:#ff6b6b,color:#fff
    style C22 fill:#ff6b6b,color:#fff
    style B22 fill:#ffd43b,color:#000
    style D22 fill:#51cf66,color:#fff
    style E22 fill:#74c0fc,color:#fff
    style F22 fill:#51cf66,color:#fff
    style G22 fill:#51cf66,color:#fff
    style H22 fill:#74c0fc,color:#fff
    style I22 fill:#b197fc,color:#fff
    style J22 fill:#b197fc,color:#fff"""
            }
        ]
    },
    "defense_immune": {
        "name": "Defense & Immune Response",
        "processes": [
            {
                "name": "Innate Immune Response Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A23[Pathogen Detection] --> B23[Pattern Recognition]
    B23 --> C23[Inflammation Initiation]
    C23 --> D23[Cytokine Release]
    D23 --> E23[Neutrophil Recruitment]
    E23 --> F23[Phagocytosis]
    F23 --> G23[Complement Activation]
    G23 --> H23[Pathogen Elimination]
    
    style A23 fill:#ff6b6b,color:#fff
    style B23 fill:#ffd43b,color:#000
    style C23 fill:#51cf66,color:#fff
    style D23 fill:#51cf66,color:#fff
    style E23 fill:#74c0fc,color:#fff
    style F23 fill:#51cf66,color:#fff
    style G23 fill:#51cf66,color:#fff
    style H23 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Adaptive Immune Response Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A24[Antigen Presentation] --> B24[T-Cell Activation]
    B24 --> C24[Clonal Selection]
    C24 --> D24[Proliferation]
    D24 --> E24[Differentiation]
    E24 --> F24[Cytotoxic T-Cells]
    E24 --> G24[Helper T-Cells]
    E24 --> H24[B-Cell Activation]
    F24 --> I24[Target Elimination]
    G24 --> I24
    H24 --> J24[Antibody Production]
    J24 --> I24
    
    style A24 fill:#ff6b6b,color:#fff
    style B24 fill:#ffd43b,color:#000
    style C24 fill:#51cf66,color:#fff
    style D24 fill:#51cf66,color:#fff
    style E24 fill:#51cf66,color:#fff
    style F24 fill:#74c0fc,color:#fff
    style G24 fill:#74c0fc,color:#fff
    style H24 fill:#74c0fc,color:#fff
    style I24 fill:#b197fc,color:#fff
    style J24 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Plant Defense Response Process",
                "organism": "Plants",
                "mermaid": """graph TD
    A25[Pathogen Recognition] --> B25[Receptor Activation]
    B25 --> C25[Signal Transduction]
    C25 --> D25[Oxidative Burst]
    D25 --> E25[Cell Death]
    C25 --> F25[Gene Expression]
    F25 --> G25[Defense Compound Synthesis]
    G25 --> H25[Systemic Acquired Resistance]
    H25 --> I25[Enhanced Protection]
    
    style A25 fill:#ff6b6b,color:#fff
    style B25 fill:#ffd43b,color:#000
    style C25 fill:#51cf66,color:#fff
    style D25 fill:#51cf66,color:#fff
    style E25 fill:#74c0fc,color:#fff
    style F25 fill:#51cf66,color:#fff
    style G25 fill:#51cf66,color:#fff
    style H25 fill:#74c0fc,color:#fff
    style I25 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Camouflage Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A26[Environmental Assessment] --> B26[Background Analysis]
    B26 --> C26[Coloration Matching]
    C26 --> D26[Pigment Adjustment]
    D26 --> E26[Pattern Formation]
    E26 --> F26[Texture Adaptation]
    F26 --> G26[Camouflage Achievement]
    G26 --> H26[Predator Avoidance]
    
    style A26 fill:#ff6b6b,color:#fff
    style B26 fill:#ffd43b,color:#000
    style C26 fill:#51cf66,color:#fff
    style D26 fill:#51cf66,color:#fff
    style E26 fill:#74c0fc,color:#fff
    style F26 fill:#74c0fc,color:#fff
    style G26 fill:#b197fc,color:#fff
    style H26 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Mimicry Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A27[Model Species] --> B27[Appearance Observation]
    C27[Mimic Species] --> B27
    B27 --> D27[Evolutionary Pressure]
    D27 --> E27[Phenotypic Variation]
    E27 --> F27{Successful Mimicry?}
    F27 -->|Yes| G27[Selection Advantage]
    F27 -->|No| H27[Predation Risk]
    G27 --> I27[Mimicry Refinement]
    H27 --> J27[Continued Selection]
    I27 --> K27[Final Mimicry Pattern]
    J27 --> E27
    
    style A27 fill:#ff6b6b,color:#fff
    style C27 fill:#ff6b6b,color:#fff
    style B27 fill:#ffd43b,color:#000
    style D27 fill:#ff6b6b,color:#fff
    style E27 fill:#ffd43b,color:#000
    style F27 fill:#74c0fc,color:#fff
    style G27 fill:#51cf66,color:#fff
    style H27 fill:#51cf66,color:#fff
    style I27 fill:#51cf66,color:#fff
    style J27 fill:#74c0fc,color:#fff
    style K27 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Chemical Defense Production",
                "organism": "Plants/Animals",
                "mermaid": """graph TD
    A28[Threat Detection] --> B28[Defense Signal]
    B28 --> C28[Gene Activation]
    C28 --> D28[Enzyme Synthesis]
    D28 --> E28[Precursor Availability]
    E28 --> F28[Toxin Biosynthesis]
    F28 --> G28[Storage/Sequestration]
    G28 --> H28[Release Mechanism]
    H28 --> I28[Defense Deployment]
    
    style A28 fill:#ff6b6b,color:#fff
    style B28 fill:#ffd43b,color:#000
    style C28 fill:#51cf66,color:#fff
    style D28 fill:#51cf66,color:#fff
    style E28 fill:#ffd43b,color:#000
    style F28 fill:#51cf66,color:#fff
    style G28 fill:#74c0fc,color:#fff
    style H28 fill:#51cf66,color:#fff
    style I28 fill:#b197fc,color:#fff"""
            }
        ]
    },
    "nutrition_metabolism": {
        "name": "Nutrition & Metabolism",
        "processes": [
            {
                "name": "Digestion Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A29[Food Ingestion] --> B29[Mechanical Breakdown]
    B29 --> C29[Enzyme Secretion]
    C29 --> D29[Chemical Breakdown]
    D29 --> E29[Carbohydrate Digestion]
    D29 --> F29[Protein Digestion]
    D29 --> G29[Lipid Digestion]
    E29 --> H29[Absorption]
    F29 --> H29
    G29 --> H29
    H29 --> I29[Transport to Cells]
    I29 --> J29[Metabolic Utilization]
    
    style A29 fill:#ff6b6b,color:#fff
    style B29 fill:#ffd43b,color:#000
    style C29 fill:#51cf66,color:#fff
    style D29 fill:#51cf66,color:#fff
    style E29 fill:#74c0fc,color:#fff
    style F29 fill:#74c0fc,color:#fff
    style G29 fill:#74c0fc,color:#fff
    style H29 fill:#51cf66,color:#fff
    style I29 fill:#74c0fc,color:#fff
    style J29 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Photosynthesis Process",
                "organism": "Plants/Algae",
                "mermaid": """graph TD
    A30[Light Energy] --> B30[Chlorophyll Absorption]
    C30[CO2] --> D30[Stomatal Entry]
    C30 --> E30[Water] --> F30[Root Uptake]
    B30 --> G30[Light Reactions]
    D30 --> H30[Calvin Cycle]
    F30 --> G30
    G30 --> I30[ATP Production]
    G30 --> J30[NADPH Production]
    G30 --> K30[O2 Release]
    I30 --> H30
    J30 --> H30
    H30 --> L30[Glucose Synthesis]
    
    style A30 fill:#ff6b6b,color:#fff
    style C30 fill:#ff6b6b,color:#fff
    style E30 fill:#ff6b6b,color:#fff
    style B30 fill:#ffd43b,color:#000
    style D30 fill:#ffd43b,color:#000
    style F30 fill:#ffd43b,color:#000
    style G30 fill:#51cf66,color:#fff
    style H30 fill:#51cf66,color:#fff
    style I30 fill:#74c0fc,color:#fff
    style J30 fill:#74c0fc,color:#fff
    style K30 fill:#b197fc,color:#fff
    style L30 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Nitrogen Fixation Process",
                "organism": "Plants/Bacteria",
                "mermaid": """graph TD
    A31[Atmospheric N2] --> B31[Nitrogenase Enzyme]
    B31 --> C31[Reduction Reaction]
    C31 --> D31[NH3 Production]
    D31 --> E31[Assimilation]
    E31 --> F31[Amino Acid Synthesis]
    F31 --> G31[Protein Formation]
    G31 --> H31[Plant Growth]
    
    style A31 fill:#ff6b6b,color:#fff
    style B31 fill:#ffd43b,color:#000
    style C31 fill:#51cf66,color:#fff
    style D31 fill:#74c0fc,color:#fff
    style E31 fill:#51cf66,color:#fff
    style F31 fill:#51cf66,color:#fff
    style G31 fill:#74c0fc,color:#fff
    style H31 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Root Nutrient Uptake Process",
                "organism": "Plants",
                "mermaid": """graph TD
    A32[Soil Nutrients] --> B32[Root Hair Contact]
    B32 --> C32[Ion Exchange]
    C32 --> D32[Active Transport]
    D32 --> E32[Symplastic Pathway]
    D32 --> F32[Apoplastic Pathway]
    E32 --> G32[Xylem Loading]
    F32 --> G32
    G32 --> H32[Upward Transport]
    
    style A32 fill:#ff6b6b,color:#fff
    style B32 fill:#ffd43b,color:#000
    style C32 fill:#51cf66,color:#fff
    style D32 fill:#51cf66,color:#fff
    style E32 fill:#74c0fc,color:#fff
    style F32 fill:#74c0fc,color:#fff
    style G32 fill:#51cf66,color:#fff
    style H32 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Predation Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A33[Prey Detection] --> B33[Stalking Approach]
    B33 --> C33[Attack Initiation]
    C33 --> D33[Capture]
    D33 --> E33[Killing]
    E33 --> F33[Handling]
    F33 --> G33[Consumption]
    G33 --> H33[Digestion]
    H33 --> I33[Energy Assimilation]
    
    style A33 fill:#ff6b6b,color:#fff
    style B33 fill:#ffd43b,color:#000
    style C33 fill:#51cf66,color:#fff
    style D33 fill:#74c0fc,color:#fff
    style E33 fill:#51cf66,color:#fff
    style F33 fill:#51cf66,color:#fff
    style G33 fill:#51cf66,color:#fff
    style H33 fill:#74c0fc,color:#fff
    style I33 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Filter Feeding Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A34[Water Current] --> B34[Particle Suspension]
    B34 --> C34[Filter Structure]
    C34 --> D34[Particle Capture]
    D34 --> E34[Retention]
    E34 --> F34[Cilia/Mucus Action]
    F34 --> G34[Transport to Mouth]
    G34 --> H34[Ingestion]
    H34 --> I34[Nutrient Extraction]
    
    style A34 fill:#ff6b6b,color:#fff
    style B34 fill:#ffd43b,color:#000
    style C34 fill:#ffd43b,color:#000
    style D34 fill:#51cf66,color:#fff
    style E34 fill:#74c0fc,color:#fff
    style F34 fill:#51cf66,color:#fff
    style G34 fill:#74c0fc,color:#fff
    style H34 fill:#51cf66,color:#fff
    style I34 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Symbiotic Nutrition Process",
                "organism": "Multiple",
                "mermaid": """graph TD
    A35[Host Organism] --> B35[Symbiont Association]
    C35[Symbiont] --> B35
    B35 --> D35[Nutrient Exchange]
    D35 --> E35[Host Benefits]
    D35 --> F35[Symbiont Benefits]
    E35 --> G35[Enhanced Nutrition]
    F35 --> H35[Protected Environment]
    G35 --> I35[Growth Advantage]
    H35 --> I35
    
    style A35 fill:#ff6b6b,color:#fff
    style C35 fill:#ff6b6b,color:#fff
    style B35 fill:#ffd43b,color:#000
    style D35 fill:#51cf66,color:#fff
    style E35 fill:#74c0fc,color:#fff
    style F35 fill:#74c0fc,color:#fff
    style G35 fill:#b197fc,color:#fff
    style H35 fill:#b197fc,color:#fff
    style I35 fill:#b197fc,color:#fff"""
            }
        ]
    },
    "sensory_perception": {
        "name": "Sensory & Perception",
        "processes": [
            {
                "name": "Vision Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A36[Light Waves] --> B36[Cornea Refraction]
    B36 --> C36[Lens Focusing]
    C36 --> D36[Retina Reception]
    D36 --> E36[Photoreceptor Activation]
    E36 --> F36[Rod Cells]
    E36 --> G36[Cone Cells]
    F36 --> H36[Signal Transduction]
    G36 --> H36
    H36 --> I36[Optic Nerve]
    I36 --> J36[Brain Processing]
    
    style A36 fill:#ff6b6b,color:#fff
    style B36 fill:#ffd43b,color:#000
    style C36 fill:#ffd43b,color:#000
    style D36 fill:#ffd43b,color:#000
    style E36 fill:#51cf66,color:#fff
    style F36 fill:#74c0fc,color:#fff
    style G36 fill:#74c0fc,color:#fff
    style H36 fill:#51cf66,color:#fff
    style I36 fill:#74c0fc,color:#fff
    style J36 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Hearing Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A37[Sound Waves] --> B37[Outer Ear Collection]
    B37 --> C37[Eardrum Vibration]
    C37 --> D37[Middle Ear Bones]
    D37 --> E37[Cochlear Fluid]
    E37 --> F37[Hair Cell Activation]
    F37 --> G37[Frequency Analysis]
    G37 --> H37[Auditory Nerve]
    H37 --> I37[Brain Interpretation]
    
    style A37 fill:#ff6b6b,color:#fff
    style B37 fill:#ffd43b,color:#000
    style C37 fill:#ffd43b,color:#000
    style D37 fill:#ffd43b,color:#000
    style E37 fill:#ffd43b,color:#000
    style F37 fill:#51cf66,color:#fff
    style G37 fill:#51cf66,color:#fff
    style H37 fill:#74c0fc,color:#fff
    style I37 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Olfaction Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A38[Odorant Molecules] --> B38[Nasal Cavity Entry]
    B38 --> C38[Olfactory Epithelium]
    C38 --> D38[Receptor Binding]
    D38 --> E38[Signal Transduction]
    E38 --> F38[Olfactory Bulb]
    F38 --> G38[Pattern Recognition]
    G38 --> H38[Odor Identification]
    
    style A38 fill:#ff6b6b,color:#fff
    style B38 fill:#ffd43b,color:#000
    style C38 fill:#ffd43b,color:#000
    style D38 fill:#51cf66,color:#fff
    style E38 fill:#51cf66,color:#fff
    style F38 fill:#74c0fc,color:#fff
    style G38 fill:#51cf66,color:#fff
    style H38 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Gustation Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A39[Taste Molecules] --> B39[Saliva Dissolution]
    B39 --> C39[Taste Receptor Binding]
    C39 --> D39[Sweet Receptors]
    C39 --> E39[Salty Receptors]
    C39 --> F39[Sour Receptors]
    C39 --> G39[Bitter Receptors]
    C39 --> H39[Umami Receptors]
    D39 --> I39[Signal Integration]
    E39 --> I39
    F39 --> I39
    G39 --> I39
    H39 --> I39
    I39 --> J39[Flavor Perception]
    
    style A39 fill:#ff6b6b,color:#fff
    style B39 fill:#ffd43b,color:#000
    style C39 fill:#51cf66,color:#fff
    style D39 fill:#74c0fc,color:#fff
    style E39 fill:#74c0fc,color:#fff
    style F39 fill:#74c0fc,color:#fff
    style G39 fill:#74c0fc,color:#fff
    style H39 fill:#74c0fc,color:#fff
    style I39 fill:#51cf66,color:#fff
    style J39 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Tactile Sensation Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A40[Mechanical Stimulus] --> B40[Touch Receptor]
    B40 --> C40[Pressure Detection]
    B40 --> D40[Vibration Detection]
    B40 --> E40[Temperature Detection]
    C40 --> F40[Signal Generation]
    D40 --> F40
    E40 --> F40
    F40 --> G40[Sensory Neuron]
    G40 --> H40[Spinal Cord]
    H40 --> I40[Brain Processing]
    
    style A40 fill:#ff6b6b,color:#fff
    style B40 fill:#ffd43b,color:#000
    style C40 fill:#51cf66,color:#fff
    style D40 fill:#51cf66,color:#fff
    style E40 fill:#51cf66,color:#fff
    style F40 fill:#51cf66,color:#fff
    style G40 fill:#74c0fc,color:#fff
    style H40 fill:#74c0fc,color:#fff
    style I40 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Photoperiod Sensing Process",
                "organism": "Plants/Animals",
                "mermaid": """graph TD
    A41[Light/Dark Cycle] --> B41[Photoreceptor Activation]
    B41 --> C41[Circadian Clock]
    C41 --> D41[Time Measurement]
    D41 --> E41{Season?}
    E41 -->|Long Day| F41[Long-Day Response]
    E41 -->|Short Day| G41[Short-Day Response]
    F41 --> H41[Physiological Change]
    G41 --> H41
    H41 --> I41[Seasonal Adaptation]
    
    style A41 fill:#ff6b6b,color:#fff
    style B41 fill:#ffd43b,color:#000
    style C41 fill:#ffd43b,color:#000
    style D41 fill:#51cf66,color:#fff
    style E41 fill:#74c0fc,color:#fff
    style F41 fill:#74c0fc,color:#fff
    style G41 fill:#74c0fc,color:#fff
    style H41 fill:#51cf66,color:#fff
    style I41 fill:#b197fc,color:#fff"""
            }
        ]
    },
    "transport_circulation": {
        "name": "Transport & Circulation",
        "processes": [
            {
                "name": "Blood Circulation Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A42[Heart Contraction] --> B42[Ventricle Ejection]
    B42 --> C42[Arterial Flow]
    C42 --> D42[Capillary Exchange]
    D42 --> E42[O2 Delivery]
    D42 --> F42[CO2 Removal]
    D42 --> G42[Nutrient Delivery]
    E42 --> H42[Venous Return]
    F42 --> H42
    G42 --> H42
    H42 --> I42[Atrial Filling]
    I42 --> A42
    
    style A42 fill:#ff6b6b,color:#fff
    style B42 fill:#ffd43b,color:#000
    style C42 fill:#51cf66,color:#fff
    style D42 fill:#51cf66,color:#fff
    style E42 fill:#74c0fc,color:#fff
    style F42 fill:#74c0fc,color:#fff
    style G42 fill:#74c0fc,color:#fff
    style H42 fill:#51cf66,color:#fff
    style I42 fill:#74c0fc,color:#fff"""
            },
            {
                "name": "Xylem Transport Process",
                "organism": "Plants",
                "mermaid": """graph TD
    A43[Root Water Uptake] --> B43[Osmotic Pressure]
    B43 --> C43[Transpiration Pull]
    C43 --> D43[Xylem Vessels]
    D43 --> E43[Cohesion-Tension]
    E43 --> F43[Upward Movement]
    F43 --> G43[Leaf Delivery]
    G43 --> H43[Transpiration]
    
    style A43 fill:#ff6b6b,color:#fff
    style C43 fill:#ff6b6b,color:#fff
    style B43 fill:#ffd43b,color:#000
    style D43 fill:#ffd43b,color:#000
    style E43 fill:#51cf66,color:#fff
    style F43 fill:#51cf66,color:#fff
    style G43 fill:#74c0fc,color:#fff
    style H43 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Phloem Transport Process",
                "organism": "Plants",
                "mermaid": """graph TD
    A44[Source Tissue] --> B44[Sugar Loading]
    B44 --> C44[Sieve Elements]
    C44 --> D44[Pressure Flow]
    D44 --> E44[Bulk Flow]
    E44 --> F44[Sink Tissue]
    F44 --> G44[Sugar Unloading]
    G44 --> H44[Utilization/Storage]
    
    style A44 fill:#ff6b6b,color:#fff
    style F44 fill:#ff6b6b,color:#fff
    style B44 fill:#ffd43b,color:#000
    style C44 fill:#ffd43b,color:#000
    style D44 fill:#51cf66,color:#fff
    style E44 fill:#51cf66,color:#fff
    style G44 fill:#51cf66,color:#fff
    style H44 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Gas Exchange Process",
                "organism": "Animals/Plants",
                "mermaid": """graph TD
    A45[Respiratory Surface] --> B45[Partial Pressure Gradient]
    B45 --> C45[O2 Diffusion In]
    B45 --> D45[CO2 Diffusion Out]
    C45 --> E45[Transport Medium]
    D45 --> F45[Atmosphere]
    E45 --> G45[Tissue Delivery]
    G45 --> H45[Cellular Respiration]
    
    style A45 fill:#ff6b6b,color:#fff
    style B45 fill:#ffd43b,color:#000
    style C45 fill:#51cf66,color:#fff
    style D45 fill:#51cf66,color:#fff
    style E45 fill:#74c0fc,color:#fff
    style F45 fill:#b197fc,color:#fff
    style G45 fill:#74c0fc,color:#fff
    style H45 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Osmoregulation Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A46[Water Intake] --> B46[Ion Balance Detection]
    C46[Salt Intake] --> B46
    B46 --> D46{Kidney Function}
    D46 --> E46[Filtration]
    E46 --> F46[Reabsorption]
    F46 --> G46[Secretion]
    G46 --> H46[Urine Formation]
    H46 --> I46[Water Balance]
    
    style A46 fill:#ff6b6b,color:#fff
    style C46 fill:#ff6b6b,color:#fff
    style B46 fill:#ffd43b,color:#000
    style D46 fill:#74c0fc,color:#fff
    style E46 fill:#51cf66,color:#fff
    style F46 fill:#51cf66,color:#fff
    style G46 fill:#51cf66,color:#fff
    style H46 fill:#74c0fc,color:#fff
    style I46 fill:#b197fc,color:#fff"""
            }
        ]
    },
    "coordination_control": {
        "name": "Coordination & Control",
        "processes": [
            {
                "name": "Endocrine Signaling Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A47[Stimulus Detection] --> B47[Hormone Synthesis]
    B47 --> C47[Gland Secretion]
    C47 --> D47[Blood Transport]
    D47 --> E47[Target Tissue]
    E47 --> F47[Receptor Binding]
    F47 --> G47[Signal Transduction]
    G47 --> H47[Cellular Response]
    
    style A47 fill:#ff6b6b,color:#fff
    style B47 fill:#ffd43b,color:#000
    style C47 fill:#51cf66,color:#fff
    style D47 fill:#74c0fc,color:#fff
    style E47 fill:#ffd43b,color:#000
    style F47 fill:#51cf66,color:#fff
    style G47 fill:#51cf66,color:#fff
    style H47 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Nervous System Signaling Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A48[Neuron Stimulation] --> B48[Action Potential]
    B48 --> C48[Axon Propagation]
    C48 --> D48[Synaptic Terminal]
    D48 --> E48[Neurotransmitter Release]
    E48 --> F48[Receptor Binding]
    F48 --> G48[Post-Synaptic Response]
    G48 --> H48[Signal Transmission]
    
    style A48 fill:#ff6b6b,color:#fff
    style B48 fill:#ffd43b,color:#000
    style C48 fill:#51cf66,color:#fff
    style D48 fill:#74c0fc,color:#fff
    style E48 fill:#51cf66,color:#fff
    style F48 fill:#51cf66,color:#fff
    style G48 fill:#74c0fc,color:#fff
    style H48 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Plant Hormone Response Process",
                "organism": "Plants",
                "mermaid": """graph TD
    A49[Hormone Production] --> B49[Auxin]
    A49 --> C49[Cytokinin]
    A49 --> D49[Gibberellin]
    A49 --> E49[Abscisic Acid]
    A49 --> F49[Ethylene]
    B49 --> G49[Target Response]
    C49 --> G49
    D49 --> G49
    E49 --> G49
    F49 --> G49
    G49 --> H49[Growth/Development]
    
    style A49 fill:#ff6b6b,color:#fff
    style B49 fill:#ffd43b,color:#000
    style C49 fill:#ffd43b,color:#000
    style D49 fill:#ffd43b,color:#000
    style E49 fill:#ffd43b,color:#000
    style F49 fill:#ffd43b,color:#000
    style G49 fill:#51cf66,color:#fff
    style H49 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Tropism Response Process",
                "organism": "Plants",
                "mermaid": """graph TD
    A50[Environmental Stimulus] --> B50[Directional Cue]
    B50 --> C50[Phototropism]
    B50 --> D50[Gravitropism]
    B50 --> E50[Thigmotropism]
    C50 --> F50[Hormone Redistribution]
    D50 --> F50
    E50 --> F50
    F50 --> G50[Asymmetric Growth]
    G50 --> H50[Orientation Change]
    
    style A50 fill:#ff6b6b,color:#fff
    style B50 fill:#ffd43b,color:#000
    style C50 fill:#74c0fc,color:#fff
    style D50 fill:#74c0fc,color:#fff
    style E50 fill:#74c0fc,color:#fff
    style F50 fill:#51cf66,color:#fff
    style G50 fill:#74c0fc,color:#fff
    style H50 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Circadian Rhythm Process",
                "organism": "Multiple",
                "mermaid": """graph TD
    A51[Light/Dark Input] --> B51[Clock Gene Expression]
    B51 --> C51[Transcriptional Loop]
    C51 --> D51[Protein Accumulation]
    D51 --> E51[Feedback Inhibition]
    E51 --> B51
    D51 --> F51[Output Pathways]
    F51 --> G51[Physiological Rhythms]
    
    style A51 fill:#ff6b6b,color:#fff
    style B51 fill:#ffd43b,color:#000
    style C51 fill:#51cf66,color:#fff
    style D51 fill:#74c0fc,color:#fff
    style E51 fill:#51cf66,color:#fff
    style F51 fill:#51cf66,color:#fff
    style G51 fill:#b197fc,color:#fff"""
            },
            {
                "name": "Homeostatic Regulation Process",
                "organism": "Animals",
                "mermaid": """graph TD
    A52[Parameter Measurement] --> B52[Set Point Comparison]
    B52 --> C52{Deviation?}
    C52 -->|Yes| D52[Control System Activation]
    C52 -->|No| E52[Maintenance]
    D52 --> F52[Effector Response]
    F52 --> G52[Parameter Correction]
    G52 --> A52
    E52 --> A52
    
    style A52 fill:#ff6b6b,color:#fff
    style B52 fill:#ffd43b,color:#000
    style C52 fill:#74c0fc,color:#fff
    style D52 fill:#51cf66,color:#fff
    style E52 fill:#b197fc,color:#fff
    style F52 fill:#51cf66,color:#fff
    style G52 fill:#74c0fc,color:#fff"""
            }
        ]
    }
}

# 5-color scheme
COLOR_SCHEME = {
    "red": {"hex": "#ff6b6b", "category": "Triggers & Inputs"},
    "yellow": {"hex": "#ffd43b", "category": "Structures & Objects"},
    "green": {"hex": "#51cf66", "category": "Processing & Operations"},
    "blue": {"hex": "#74c0fc", "category": "Intermediates & States"},
    "violet": {"hex": "#b197fc", "category": "Products & Outputs"}
}

def count_mermaid_elements(mermaid_code: str):
    """Count nodes, edges, conditionals, and gates in Mermaid code"""
    nodes = set()
    edges = 0
    conditionals = 0
    or_gates = 0
    and_gates = 0
    
    lines = mermaid_code.split('\n')
    for line in lines:
        line = line.strip()
        if '-->' in line:
            edges += 1
            parts = re.findall(r'(\w+)\[.*?\]|(\w+)\{.*?\}', line)
            for part in parts:
                node = part[0] or part[1]
                if node:
                    nodes.add(node)
            if '{' in line and '}' in line:
                conditionals += 1
        
        if re.search(r'\{.*?OR.*?\}', line, re.IGNORECASE):
            or_gates += 1
        if re.search(r'\{.*?AND.*?\}', line, re.IGNORECASE):
            and_gates += 1
    
    return len(nodes), edges, conditionals, or_gates, and_gates

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

def create_biology_database():
    """Create the complete biology processes database"""
    base_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space/biology-processes-database")
    processes_dir = base_dir / "processes"
    processes_dir.mkdir(parents=True, exist_ok=True)
    
    all_processes_metadata = []
    process_count_by_category = {}
    total_nodes = 0
    total_edges = 0
    total_conditionals = 0
    total_or_gates = 0
    total_and_gates = 0
    
    for category_slug, category_data in BIOLOGY_PROCESSES.items():
        category_name = category_data["name"]
        category_dir = processes_dir / category_slug
        category_dir.mkdir(parents=True, exist_ok=True)
        process_count_by_category[category_slug] = 0
        
        print(f"\nProcessing category: {category_name}")
        
        for process_data in category_data["processes"]:
            process_name = process_data["name"]
            organism = process_data.get("organism", "General")
            mermaid_code = process_data["mermaid"]
            
            # Count complexity
            nodes, edges, conditionals, or_gates, and_gates = count_mermaid_elements(mermaid_code)
            
            if nodes < 15:
                complexity_level = "low"
            elif nodes < 30:
                complexity_level = "medium"
            else:
                complexity_level = "high"
            
            process_id = f"{category_slug}-{slugify(process_name)}"
            
            # Create description
            description = f"{process_name} in {organism}. This process represents a higher-level biological mechanism distinct from molecular/biochemical processes covered in GLMP."
            
            # Create JSON file
            json_data = {
                "id": process_id,
                "name": process_name,
                "category": "biology",
                "subcategory": category_slug,
                "subcategory_name": category_name,
                "organism": organism,
                "description": description,
                "complexity": {
                    "nodes": nodes,
                    "edges": edges,
                    "conditionals": conditionals,
                    "logicGates": {
                        "orGates": or_gates,
                        "andGates": and_gates,
                        "total": or_gates + and_gates
                    },
                    "level": complexity_level,
                    "detailLevel": complexity_level
                },
                "colorScheme": COLOR_SCHEME,
                "mermaid": mermaid_code,
                "sources": [{
                    "title": "Programming Framework: A Universal Process Visualization Methodology",
                    "authors": "Welz, G.",
                    "journal": "CopernicusAI Knowledge Engine",
                    "year": "2025",
                    "url": "https://huggingface.co/spaces/garywelz/programming_framework",
                    "notes": f"Higher-level biological process visualization: {process_name}. Created using the Programming Framework methodology for organismal and ecological process analysis."
                }],
                "keywords": list(set(slugify(process_name).split('-') + slugify(category_name).split('-') + [organism.lower()])),
                "relatedProcesses": [],
                "created": "2026-01-08",
                "lastUpdated": "2026-01-08",
                "verified": False,
                "notes": f"Higher-level biological process. GLMP covers biochemical/molecular processes; this database covers organismal/ecological processes."
            }
            
            json_file = category_dir / f"{process_id}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"  ✓ Created: {json_file.name}")
            
            all_processes_metadata.append({
                "id": process_id,
                "name": process_name,
                "subcategory": category_slug,
                "subcategory_name": category_name,
                "organism": organism,
                "complexity": complexity_level,
                "nodes": nodes,
                "edges": edges,
                "orGates": or_gates,
                "andGates": and_gates,
                "totalGates": or_gates + and_gates
            })
            
            process_count_by_category[category_slug] += 1
            total_nodes += nodes
            total_edges += edges
            total_conditionals += conditionals
            total_or_gates += or_gates
            total_and_gates += and_gates
    
    # Create metadata.json
    metadata_json = {
        "name": "Biology Processes Database",
        "version": "1.0.0",
        "created": "2026-01-08",
        "lastUpdated": "2026-01-08",
        "category": "biology",
        "colorScheme": "5-color",
        "description": "Higher-level biological processes visualized using the Programming Framework with 5-color scheme. This database complements GLMP by focusing on organismal, developmental, behavioral, ecological, and physiological processes rather than molecular/biochemical processes.",
        "totalProcesses": len(all_processes_metadata),
        "subcategories": len(process_count_by_category),
        "statistics": {
            "totalNodes": total_nodes,
            "totalEdges": total_edges,
            "totalConditionals": total_conditionals,
            "totalOrGates": total_or_gates,
            "totalAndGates": total_and_gates,
            "totalGates": total_or_gates + total_and_gates
        },
        "subcategoryCounts": process_count_by_category,
        "processes": all_processes_metadata
    }
    
    metadata_file = base_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Created metadata.json")
    print(f"  Total processes: {len(all_processes_metadata)}")
    print(f"  Total categories: {len(process_count_by_category)}")
    print(f"  Total nodes: {total_nodes}")
    print(f"  Total edges: {total_edges}")
    
    return base_dir

if __name__ == "__main__":
    print("=" * 60)
    print("Biology Processes Database Generator")
    print("=" * 60)
    create_biology_database()
    print("\n" + "=" * 60)
    print("Database creation complete!")
    print("=" * 60)
