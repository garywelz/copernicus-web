# Proposal Enhancement Plan: Integrating Paper 4 (Knowledge Engine Concept) into NSF and DOE Proposals

**Date:** December 25, 2024  
**Status:** Planning Document  
**Purpose:** Enhance NSF CISE CORE and DOE SBIR Phase I proposals with theoretical framework and insights from Paper 4

---

## Executive Summary

Paper 4 ("A Vision for AI-Powered Knowledge Engines") provides a comprehensive theoretical framework that significantly strengthens both proposals by:

1. **Establishing intellectual foundation**: The "Knowledge Engine" concept provides a unifying theoretical framework
2. **Demonstrating broader vision**: Shows how CopernicusAI fits into a larger research agenda
3. **Strengthening related work**: Comprehensive synthesis of 70 years of AI research
4. **Providing evaluation framework**: Detailed evaluation plans and success criteria
5. **Adding visual component**: Architecture diagram enhances technical description

**Recommendation**: Both proposals would benefit substantially from selective integration of Paper 4 content, particularly the theoretical framework, capability taxonomy, and evaluation methodology.

---

## 1. Assessment: Current Proposal Strengths and Gaps

### NSF Proposal Current State

**Strengths:**
- Strong focus on practical implementation (CopernicusAI, Programming Framework, GLMP)
- Clear technical objectives and deliverables
- Good coverage of multi-modal integration
- MCP server integration mentioned
- Evaluation plans present but could be more detailed

**Gaps/Enhancement Opportunities:**
- Limited theoretical framework (focuses on implementation)
- Could benefit from broader vision positioning
- Related work could be more comprehensive
- Evaluation methodology could reference established frameworks
- Missing visual architecture diagram
- Character/ethos specifications not emphasized

### DOE Proposal Current State

**Strengths:**
- Strong commercial focus and market opportunity
- Clear Phase I/II objectives
- Good prior work evidence
- Practical reliability mechanisms

**Gaps/Enhancement Opportunities:**
- Limited theoretical foundation
- Could emphasize broader research agenda
- Evaluation plans less detailed
- Missing architecture visualization
- Character specifications not mentioned

---

## 2. Key Content from Paper 4 to Integrate

### 2.1 Theoretical Framework: Knowledge Engine Concept

**From Paper 4:**
- Definition of "Knowledge Engine" as systematic framework
- Historical grounding (Aristotle, Newton, Euler, Copernicus)
- Nine-capability taxonomy (ingestion, digestion, analysis, calculation, comparison, connection, association, analogy, communication)
- Integration challenge: capabilities must work together systematically

**Integration Strategy:**
- Add to NSF Introduction/Motivation section
- Position CopernicusAI as instantiation of Knowledge Engine framework
- Reference in DOE Technical Problem section

### 2.2 Comprehensive Related Work

**From Paper 4:**
- Expert Systems (1970s-1990s): MYCIN, DENDRAL, Cyc - limitations and lessons
- Knowledge Representation: Semantic networks, ontologies, Semantic Web
- Modern Systems: Watson, Google Knowledge Graph, Wolfram Alpha, OpenAlex
- Cognitive Architectures: SOAR, ACT-R, CLARION
- RAG and Modern Retrieval: Lewis et al. 2020, Karpukhin et al. 2020

**Integration Strategy:**
- Expand NSF Related Work section (currently brief)
- Add to DOE Prior Work section
- Show how CopernicusAI addresses historical limitations

### 2.3 Character/Ethos Specifications

**From Paper 4:**
- Explorer ethos concept (curiosity, fearlessness, conceptual freedom)
- Character specification mechanism (copernicus.character.json)
- Concrete implementation example with behavioral parameters
- Validation status and evaluation plans

**Integration Strategy:**
- Add to NSF Intellectual Merit (novel contribution)
- Mention in DOE Phase I objectives as exploratory direction
- Reference in evaluation plans

### 2.4 Architecture Diagram

**From Paper 4:**
- Visual flowchart showing CopernicusAI architecture
- Uses Programming Framework five-color system
- Shows data flow from ingestion to communication
- Demonstrates integration of components

**Integration Strategy:**
- Add Figure 1 to NSF Technical Approach section
- Add to DOE Proposed Innovation section
- Enhances visual understanding of system

### 2.5 Evaluation Framework

**From Paper 4:**
- Detailed evaluation plans (Section 7.6)
- Success criteria with quantitative thresholds
- Multiple evaluation dimensions (retrieval, connections, user studies, character specs)
- Timeline for evaluation (6-24 months)

**Integration Strategy:**
- Enhance NSF Research Methods and Evaluation section
- Add to DOE Phase I evaluation objectives
- Provide concrete metrics and baselines

### 2.6 Framework Requirement Argument

**From Paper 4:**
- Argument that ambitious goals require comprehensive frameworks
- Not just scaling models, but building scaffolding
- Seven requirements for knowledge engines (ingestion, multi-modal analysis, hypothesis generation, etc.)

**Integration Strategy:**
- Add to NSF Motivation section
- Strengthen DOE Technical Problem section
- Shows why comprehensive approach is necessary

---

## 3. Detailed Enhancement Plan: NSF Proposal

### 3.1 Project Summary (1 page) - Enhancements

**Current:** Focuses on practical components (briefings, metadata, process visualization)

**Enhancements:**
1. **Add theoretical positioning** (1-2 sentences):
   - "This project instantiates a 'Knowledge Engine' framework—a systematic approach to AI-powered knowledge discovery that integrates nine core capabilities (ingestion, digestion, analysis, calculation, comparison, connection, association, analogy, communication) into a unified system."

2. **Strengthen Intellectual Merit** (add bullet):
   - "**Knowledge Engine framework instantiation:** First systematic implementation of a comprehensive knowledge engine framework synthesizing 70 years of AI research, from expert systems to modern RAG, addressing historical limitations (brittleness, knowledge acquisition bottlenecks) through modern AI while maintaining benefits of structured representation."

**Word Count Impact:** +50-75 words (must stay within 1 page)

### 3.2 Introduction and Motivation - Enhancements

**Section 1.1 Problem Statement** - Add:
- Reference to "fragmentation of knowledge discovery tools" as broader problem
- Position within Knowledge Engine framework

**New Section 1.4: Theoretical Foundation**
- Add 1-2 paragraphs on Knowledge Engine concept
- Reference historical knowledge engines (Aristotle, Newton, etc.)
- Introduce nine-capability taxonomy
- Position CopernicusAI as instantiation

**Section 1.3 Prior Work** - Enhance:
- Add subsection on "Knowledge Engine Framework" referencing Paper 4
- Mention character/ethos specifications as exploratory direction

### 3.3 Research Objectives - Enhancements

**Add to Objective 1 or create new objective:**
- "**Objective 5: Knowledge Engine Framework Validation** (Exploratory)
  - Implement and evaluate character/ethos specifications (copernicus.character.json)
  - A/B testing comparing character-modified vs. baseline search
  - Measure impact on knowledge discovery outcomes
  - This represents an exploratory direction requiring validation"

### 3.4 Technical Approach - Enhancements

**Add Architecture Diagram:**
- Include Figure 1 from Paper 4 (CopernicusAI System Architecture)
- Reference in text: "Figure 1 shows the CopernicusAI architecture using the Programming Framework's five-color system, demonstrating the flow from data sources through processing, storage, analysis, and communication layers."

**Expand Section on Integration:**
- Reference nine-capability taxonomy
- Explain how components map to capabilities
- Emphasize systematic integration (not just individual components)

**Add Character Specification Subsection:**
- Brief description of copernicus.character.json
- How it influences search and prioritization
- Note: exploratory, requires validation

### 3.5 Research Methods and Evaluation - Enhancements

**Expand Evaluation Section:**
- Reference Paper 4 Section 7.6 (Preliminary Observations and Future Evaluation Plans)
- Add specific metrics:
  - Retrieval Quality: Precision@10, Recall@10, MRR, nDCG
  - Connection Discovery: >60% valid connections (expert evaluation)
  - User Value: Surveys, interviews, task completion time
  - Character Specification: A/B testing, diversity metrics

**Add Baseline Comparisons:**
- PubMed, Google Scholar, Semantic Scholar
- Specific success criteria (parity or better)

**Add Timeline:**
- Short-term (6-12 months): Retrieval quality evaluation
- Medium-term (12-24 months): User studies, character specification A/B testing
- Long-term (24+ months): Longitudinal impact study

### 3.6 Related Work - Enhancements

**Expand significantly using Paper 4 Section 2:**
- Add subsection on Expert Systems (MYCIN, DENDRAL, Cyc) and their limitations
- Add subsection on Knowledge Representation (semantic networks, ontologies, Semantic Web)
- Add subsection on Modern Systems (Watson, Knowledge Graph, Wolfram Alpha, OpenAlex)
- Add subsection on Cognitive Architectures (SOAR, ACT-R, CLARION)
- Add subsection on RAG and Modern Retrieval (Lewis et al. 2020, Karpukhin et al. 2020)
- Show how CopernicusAI addresses historical limitations

**Page Count Impact:** +2-3 pages (must stay within 15-page limit for Project Description)

### 3.7 Expected Outcomes - Enhancements

**Add:**
- "Publication of Knowledge Engine framework paper (currently in draft, targeting workshop/conference submission)"
- "Validation of character/ethos specification approach (if successful)"
- "Open-source Knowledge Engine framework documentation"

---

## 4. Detailed Enhancement Plan: DOE Proposal

### 4.1 Technical Problem - Enhancements

**Add theoretical context:**
- Reference Knowledge Engine framework
- Position market opportunity within broader research agenda
- Add 1-2 sentences on why comprehensive frameworks are needed (not just scaling models)

### 4.2 Proposed Innovation - Enhancements

**Add to Innovation (a):**
- Mention character/ethos specifications as exploratory direction
- Reference Knowledge Engine framework

**Add new Innovation (d):**
- "**(d) Knowledge Engine Framework Instantiation**
  - CopernicusAI represents the first systematic implementation of a comprehensive Knowledge Engine framework
  - Integrates nine core capabilities (ingestion, digestion, analysis, calculation, comparison, connection, association, analogy, communication)
  - Addresses historical limitations of expert systems through modern AI
  - Character/ethos specifications enable behavioral customization (exploratory)"

### 4.3 Phase I Technical Objectives - Enhancements

**Add to Objective 1:**
- Reference Knowledge Engine framework
- Mention character specifications as exploratory component

**Add new Objective 5 (Exploratory):**
- "**Objective 5 — Character/Ethos Specification Evaluation (Exploratory)**
  - Implement copernicus.character.json behavioral parameters
  - A/B testing: character-modified vs. baseline search
  - Measure impact on result diversity, paradigm-challenging emphasis, user preference
  - This is exploratory; validation required to determine practical value"

### 4.4 Prior Work Evidence - Enhancements

**Add:**
- Reference to Paper 4 (Knowledge Engine Concept) as theoretical foundation
- Mention MCP server implementation (already mentioned, but can expand)
- Reference architecture diagram from Paper 4

### 4.5 Evaluation and Validation - Enhancements

**Expand using Paper 4 Section 7.6:**
- Add specific metrics (Precision@10, Recall@10, etc.)
- Add baseline comparisons (PubMed, Google Scholar)
- Add success criteria (>60% valid connections)
- Add timeline (6-24 months)

---

## 5. Implementation Strategy

### Phase 1: High-Impact, Low-Effort Enhancements (1-2 hours)

1. **Add Architecture Diagram** to both proposals
   - Copy Figure 1 from Paper 4
   - Add caption referencing Programming Framework
   - Insert in Technical Approach section

2. **Add Knowledge Engine Framework Reference** to summaries
   - 1-2 sentences in Project Summary (NSF)
   - 1-2 sentences in Technical Problem (DOE)

3. **Add Character Specification Mention**
   - Brief note in Intellectual Merit (NSF)
   - Brief note in Proposed Innovation (DOE)

### Phase 2: Medium-Impact Enhancements (3-4 hours)

1. **Expand Related Work** (NSF)
   - Add subsections from Paper 4 Section 2
   - Show how CopernicusAI addresses historical limitations
   - Stay within 15-page limit

2. **Enhance Evaluation Sections**
   - Add specific metrics from Paper 4
   - Add baseline comparisons
   - Add success criteria

3. **Add Theoretical Foundation Section** (NSF)
   - New Section 1.4 on Knowledge Engine framework
   - Reference nine-capability taxonomy
   - Position CopernicusAI as instantiation

### Phase 3: Comprehensive Enhancements (6-8 hours)

1. **Full Integration of Knowledge Engine Framework**
   - Throughout both proposals
   - Consistent terminology
   - Clear positioning

2. **Expand Character Specification Content**
   - Detailed description in Technical Approach
   - Evaluation plans
   - Success criteria

3. **Comprehensive Related Work Expansion**
   - Full integration of Paper 4 Section 2
   - Proper citations
   - Clear positioning

---

## 6. Specific Text Additions

### 6.1 NSF Project Summary Addition

**Add to Intellectual Merit (after existing bullets):**

"**Knowledge Engine Framework Instantiation:** This project represents the first systematic implementation of a comprehensive 'Knowledge Engine' framework—a synthesizing approach integrating 70 years of AI research from expert systems to modern retrieval-augmented generation. The framework proposes nine integrated capabilities (ingestion, digestion, analysis, calculation, comparison, connection, association, analogy, communication) that must work together systematically. CopernicusAI instantiates this framework, addressing historical limitations of expert systems (brittleness, knowledge acquisition bottlenecks) through modern AI while maintaining benefits of structured representation. Additionally, the project explores character/ethos specifications as a novel direction for guiding knowledge discovery behavior, though this requires validation."

### 6.2 NSF Introduction Addition

**New Section 1.4: Theoretical Foundation - Knowledge Engine Framework**

"This project is grounded in a 'Knowledge Engine' framework—a systematic approach to understanding how intelligent systems, both human and artificial, discover, integrate, and generate knowledge. Historical knowledge engines—from Aristotle's systematic categorization to Newton's mathematical synthesis to Euler's pattern exploration—reveal common patterns: systematic ingestion of information, analytical digestion, pattern identification, generative output, and iterative refinement.

Modern AI enables computational knowledge engines that combine the systematic rigor of historical knowledge creators with capabilities exceeding human limitations in scale, speed, and persistence. However, creating such systems requires more than applying AI tools—it requires understanding the systematic processes that make knowledge engines effective.

We propose a taxonomy of nine integrated capabilities that knowledge engines must combine systematically: (1) ingestion—multi-source, multi-modal acquisition; (2) digestion—processing into structured forms; (3) analysis—deep examination identifying patterns; (4) calculation—mathematical computation and simulation; (5) comparison—similarity assessment and cross-domain comparison; (6) connection—relationship discovery and network analysis; (7) association—co-occurrence detection and correlation analysis; (8) analogy—structural mapping across domains; and (9) communication—multi-modal expression.

The power of a knowledge engine lies not in any single capability, but in their systematic integration. CopernicusAI instantiates this framework, demonstrating how these capabilities can be integrated into a unified research platform. This theoretical foundation provides the intellectual structure for the technical contributions described in this proposal."

### 6.3 DOE Technical Problem Addition

**Add to end of Section 1:**

"This market opportunity aligns with a broader research agenda: the development of 'Knowledge Engines'—systematic frameworks for AI-powered knowledge discovery. Simply scaling AI models is insufficient for ambitious goals like 'finding a cure for cancer.' Such goals require comprehensive frameworks combining multiple capabilities, structured processes, specialized tools, and systematic approaches. CopernicusAI represents an early instantiation of this Knowledge Engine framework, demonstrating feasibility while requiring extensive validation."

### 6.4 DOE Proposed Innovation Addition

**Add new subsection (d):**

"**(d) Knowledge Engine Framework Instantiation**

CopernicusAI represents the first systematic implementation of a comprehensive Knowledge Engine framework—a synthesizing approach integrating 70 years of AI research. The framework proposes nine integrated capabilities (ingestion, digestion, analysis, calculation, comparison, connection, association, analogy, communication) that must work together systematically. This framework addresses historical limitations of expert systems (brittleness, knowledge acquisition bottlenecks) through modern AI while maintaining benefits of structured representation.

Additionally, CopernicusAI explores character/ethos specifications as a novel direction for guiding knowledge discovery behavior. The system implements `copernicus.character.json` with behavioral parameters (e.g., fearlessness, empirical focus, revolutionary thinking) that influence search prioritization and content selection. For example, papers containing 'challenge,' 'refute,' or 'paradigm shift' receive relevance boosts when fearlessness parameters are high. This is an exploratory direction requiring validation to determine practical value."

---

## 7. Citations to Add

### From Paper 4 References:

**Expert Systems:**
- Shortliffe, E. H. (1976). Computer-Based Medical Consultations: MYCIN
- Lindsay, R. K., et al. (1980). Applications of Artificial Intelligence for Organic Chemistry: The DENDRAL Project
- Lenat, D. B. (1995). CYC: A large-scale investment in knowledge infrastructure

**Knowledge Representation:**
- Quillian, M. R. (1968). Semantic memory
- Minsky, M. (1974). A framework for representing knowledge
- Gruber, T. R. (1993). A translation approach to portable ontology specifications
- Berners-Lee, T., et al. (2001). The semantic web

**Modern Systems:**
- Ferrucci, D., et al. (2010). Building Watson: An overview of the DeepQA project
- Singhal, A. (2012). Introducing the Knowledge Graph
- Wolfram, S. (2009). Wolfram|Alpha is coming!
- Kinney, R., et al. (2023). The Semantic Scholar Open Data Platform

**Cognitive Architectures:**
- Laird, J. E. (2012). The SOAR Cognitive Architecture
- Anderson, J. R. (2007). How Can the Human Mind Occur in the Physical Universe?
- Sun, R. (2006). Cognition and Multi-Agent Interaction

**RAG and Retrieval:**
- Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks
- Karpukhin, V., et al. (2020). Dense passage retrieval for open-domain question answering

**Note:** Paper 4 itself should be cited as:
- Welz, G. (2024). A Vision for AI-Powered Knowledge Engines: A Framework for Systematic Knowledge Discovery and Integration. [arXiv preprint or workshop submission - update when published]

---

## 8. Visual Components to Add

### Architecture Diagram (Figure 1 from Paper 4)

**File:** `copernicusai_architecture.png` (already exists in papers directory)

**Caption for NSF:**
"Figure 1: CopernicusAI System Architecture. This flowchart uses the Programming Framework's five-color system: Red = Inputs/Data Sources, Yellow = Structures/Storage, Green = Processing/Operations, Blue = Decision Points/Intermediates, Violet = Outputs/Communication. The diagram shows the flow from data sources (academic databases, literature, educational content) through ingestion, processing, storage, analysis, and communication layers. The character specification (yellow) influences processing through prompt modification and prioritization logic."

**Caption for DOE:**
"Figure 1: CopernicusAI Knowledge Engine Architecture. The system integrates nine core capabilities (ingestion, digestion, analysis, calculation, comparison, connection, association, analogy, communication) into a unified platform. Data flows from multiple sources through processing layers to storage and analysis, enabling cross-modal linking and knowledge discovery."

**Placement:**
- NSF: Section 3 (Technical Approach), after describing system components
- DOE: Section 2 (Proposed Innovation), after describing innovations

---

## 9. Page Count Considerations

### NSF Proposal

**Current:** Project Description ~12-13 pages (within 15-page limit)

**After Enhancements:**
- Architecture diagram: +0.5 pages
- Theoretical Foundation section: +1 page
- Expanded Related Work: +2-3 pages
- Enhanced Evaluation: +0.5 pages
- **Total:** ~16-18 pages (OVER LIMIT)

**Solution:**
- Condense existing content by 1-2 pages
- Move some Related Work to References section (brief citations)
- Use more concise language in some sections
- **Target:** Stay within 15-page limit

### DOE Proposal

**Current:** No strict page limit, but should be concise

**After Enhancements:**
- Architecture diagram: +0.5 pages
- Knowledge Engine framework content: +1-2 pages
- Enhanced evaluation: +0.5 pages
- **Total:** Manageable, no limit concerns

---

## 10. Risk Mitigation

### Risk 1: Page Count Exceeded (NSF)

**Mitigation:**
- Prioritize high-impact additions
- Condense existing content
- Move detailed Related Work to supplementary materials (if allowed)
- Use more concise language

### Risk 2: Over-Theorizing (Both)

**Mitigation:**
- Keep theoretical content focused and practical
- Always connect theory to implementation
- Emphasize that CopernicusAI is concrete instantiation
- Balance theory with practical deliverables

### Risk 3: Character Specifications Too Speculative

**Mitigation:**
- Always label as "exploratory"
- Emphasize "requires validation"
- Position as future research direction
- Don't over-promise

### Risk 4: Diluting Core Message

**Mitigation:**
- Keep enhancements focused
- Don't add content that doesn't strengthen core arguments
- Maintain clear narrative flow
- Review for coherence after additions

---

## 11. Implementation Checklist

### Phase 1: Quick Wins (Do First)

- [ ] Add architecture diagram (Figure 1) to both proposals
- [ ] Add 1-2 sentences on Knowledge Engine framework to summaries
- [ ] Add character specification mention (brief, exploratory)
- [ ] Add Paper 4 citation (when available)

### Phase 2: Medium Enhancements

- [ ] Add Theoretical Foundation section to NSF (Section 1.4)
- [ ] Expand Related Work in NSF (add 2-3 subsections from Paper 4)
- [ ] Enhance Evaluation sections (add metrics, baselines, success criteria)
- [ ] Add Knowledge Engine framework to DOE Technical Problem

### Phase 3: Comprehensive Integration

- [ ] Full integration of Knowledge Engine terminology throughout
- [ ] Expand Character Specification content (with appropriate hedging)
- [ ] Comprehensive Related Work expansion
- [ ] Final review for coherence and page limits

### Final Review

- [ ] Verify page counts (NSF: ≤15 pages)
- [ ] Check all citations are properly formatted
- [ ] Ensure consistent terminology
- [ ] Review for coherence and flow
- [ ] Verify all figures are included and captioned

---

## 12. Expected Benefits

### For NSF Proposal

1. **Stronger Intellectual Merit**: Theoretical framework provides deeper foundation
2. **Better Positioning**: Shows how work fits into broader research agenda
3. **Comprehensive Related Work**: Demonstrates knowledge of field
4. **Clearer Evaluation**: Specific metrics and success criteria
5. **Visual Enhancement**: Architecture diagram improves understanding

### For DOE Proposal

1. **Broader Vision**: Shows research agenda beyond Phase I
2. **Competitive Advantage**: Knowledge Engine framework differentiates from competitors
3. **Innovation Highlight**: Character specifications as novel direction
4. **Evaluation Framework**: Clear metrics for Phase I success
5. **Visual Component**: Architecture diagram enhances technical description

---

## 13. Timeline

**Week 1 (This Week):**
- Review this plan
- Decide on scope of enhancements
- Begin Phase 1 (quick wins)

**Week 2:**
- Complete Phase 1
- Begin Phase 2 (medium enhancements)
- Draft new sections

**Week 3:**
- Complete Phase 2
- Begin Phase 3 (comprehensive integration)
- First review for coherence

**Week 4:**
- Complete Phase 3
- Final review
- Page count adjustments
- Final polish

**Total Estimated Time:** 10-15 hours of focused work

---

## 14. Questions to Resolve

1. **Page Count Strategy (NSF)**: How aggressive should we be in condensing existing content?
2. **Character Specifications**: How much detail to include? (Balance: interesting vs. too speculative)
3. **Related Work Depth**: How much detail from Paper 4 to include? (Balance: comprehensive vs. page limits)
4. **Theoretical Foundation**: How much historical context (Aristotle, Newton, etc.) to include?
5. **Paper 4 Citation**: Should we cite as "in preparation," "submitted," or wait for acceptance?

---

## 15. Recommendations

### Priority 1 (Must Do)

1. **Add Architecture Diagram** - High impact, low effort, visual enhancement
2. **Add Knowledge Engine Framework Reference** - Strengthens theoretical foundation
3. **Enhance Evaluation Sections** - Provides concrete metrics and success criteria

### Priority 2 (Should Do)

1. **Expand Related Work** - Demonstrates comprehensive knowledge of field
2. **Add Theoretical Foundation Section** - Provides intellectual grounding
3. **Add Character Specification Content** - Novel direction, but keep brief and exploratory

### Priority 3 (Nice to Have)

1. **Comprehensive Related Work Expansion** - If page limits allow
2. **Detailed Character Specification** - If space permits
3. **Historical Context** - Brief mentions sufficient

---

## Conclusion

Paper 4 provides substantial content that would strengthen both proposals, particularly:
- Theoretical framework and positioning
- Comprehensive related work
- Detailed evaluation methodology
- Visual architecture diagram
- Novel research directions (character specifications)

The key is selective integration that enhances without diluting the core message or exceeding page limits. Prioritize high-impact, low-effort enhancements first, then proceed with more comprehensive integration if time and space permit.

**Next Step:** Review this plan and decide on scope of enhancements to implement.


