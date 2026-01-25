# Changelog

All notable changes to the SC2 Replay Ground Truth Extraction Pipeline project.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-01-25

### Added - Phase 7: Documentation & Deployment

**User Documentation**
- `README_SC2_PIPELINE.md` - Complete project overview and quick start
- `docs/installation.md` - Detailed installation guide with platform-specific instructions
- `docs/usage.md` - Comprehensive usage guide with code examples
- `docs/architecture.md` - System architecture and design documentation
- `docs/data_dictionary.md` - Complete output schema reference
- `docs/troubleshooting.md` - Common issues and solutions guide
- `docs/api_reference.md` - Public API documentation

**Developer Documentation**
- `CONTRIBUTING.md` - Contribution guidelines and development workflow
- `CHANGELOG.md` - This changelog
- `verify_installation.py` - Installation verification script

**Project Metadata**
- `requirements_extraction.txt` - Production dependencies
- `requirements_testing.txt` - Testing dependencies
- Updated `.gitignore` for output artifacts

**Documentation Quality**
- 6 comprehensive markdown documents (~15,000 words total)
- Code examples for all major features
- Platform-specific instructions (Windows, macOS, Linux)
- Troubleshooting guide with 20+ common issues
- Complete data dictionary with 50+ column types documented
- Architecture diagrams and data flow documentation

---

## [0.9.0] - 2026-01-25

### Added - Phase 6: Testing & Refinement

**Test Suite** (79+ tests, ~3,000 lines of code)
- Unit tests for StateExtractor (24 tests)
- Unit tests for WideTableBuilder (16 tests)
- Unit tests for OutputValidator (19 tests)
- Integration tests (12 tests)
- Performance tests (8 tests)

**Test Infrastructure**
- `tests/pytest.ini` - Pytest configuration
- `tests/conftest.py` - Shared fixtures (365 lines)
- `tests/fixtures/` - Mock data and test fixtures
- `run_tests.py` - Convenient test runner script

**Documentation**
- `tests/README.md` - Test suite documentation
- `PHASE_6_TEST_SUITE_COMPLETE.md` - Complete test deliverables
- `PHASE_6_QUICKSTART.md` - Quick start for testing
- `TEST_SUITE_SUMMARY.md` - Test suite overview

**Quality Improvements**
- Mock pysc2 classes for testing without SC2
- Comprehensive test coverage (>80% estimated)
- Fast test execution (< 30 seconds for full suite)
- CI/CD ready test structure

---

## [0.8.0] - 2026-01-25

### Added - Phase 4: Validation & Quality Assurance

**Validation System** (2 modules, 1,366 lines)
- `src_new/utils/validation.py` - OutputValidator class
- `src_new/utils/documentation.py` - Schema documentation generator
- Comprehensive data quality checks
- Validation reporting

**Features**
- Duplicate game loop detection
- Negative resource validation
- Supply cap violation checks
- Building progress monotonicity
- Unit count consistency verification
- Messages parquet validation
- Validation report generation

---

## [0.7.0] - 2026-01-25

### Added - Phase 3: Pipeline Integration

**Pipeline Components** (2 modules, 848 lines)
- `src_new/pipeline/extraction_pipeline.py` - ReplayExtractionPipeline class
- `src_new/pipeline/parallel_processor.py` - ParallelReplayProcessor class
- Two-pass processing mode (schema discovery + extraction)
- Single-pass processing mode (fast extraction)
- Batch processing with multiprocessing
- Error handling and result aggregation

**Convenience Functions**
- `process_replay_quick()` - One-line replay processing
- `process_directory_quick()` - One-line batch processing
- Retry mechanism for failed replays
- Progress tracking and statistics

**Documentation**
- `src_new/pipeline/QUICKSTART.py` - Quick start examples
- `src_new/pipeline/USAGE_EXAMPLES.md` - Usage patterns
- `src_new/pipeline/ARCHITECTURE.md` - Architecture documentation

---

## [0.6.0] - 2026-01-24

### Added - Phase 2: Core Extraction Components

**Extraction Modules** (5 modules, 1,929 lines)
- `src_new/extraction/replay_loader.py` - ReplayLoader class
- `src_new/extraction/state_extractor.py` - StateExtractor with UnitTracker and BuildingTracker
- `src_new/extraction/schema_manager.py` - SchemaManager class
- `src_new/extraction/wide_table_builder.py` - WideTableBuilder class
- `src_new/extraction/parquet_writer.py` - ParquetWriter class

**Features**
- Complete state extraction from pysc2 observations
- Unit and building lifecycle tracking
- Consistent ID assignment across frames
- Dynamic schema building
- Wide-format row generation
- Parquet file writing with compression

---

## [0.5.0] - 2026-01-24

### Added - Phase 1: Basic Extractors

**Extractor Modules** (4 modules, ~730 lines)
- `src_new/extractors/unit_extractor.py` - UnitExtractor class
- `src_new/extractors/building_extractor.py` - BuildingExtractor class
- `src_new/extractors/economy_extractor.py` - EconomyExtractor class
- `src_new/extractors/upgrade_extractor.py` - UpgradeExtractor class

**Features**
- Unit position and state extraction
- Building construction tracking
- Economy metrics (minerals, vespene, supply)
- Upgrade completion tracking
- Unit/building ID assignment
- State detection (built/existing/killed)

---

## [0.4.0] - 2026-01-24

### Added - Pipeline Infrastructure

**Core Components**
- `src_new/pipeline/replay_loader.py` - Replay loading
- `src_new/pipeline/game_loop_iterator.py` - Game loop iteration
- Project structure and module organization

---

## [0.3.0] - 2026-01-24

### Added - Planning Phase Complete

**Planning Documentation**
- `docs/planning/architecture.md` - System architecture
- `docs/planning/api_specifications.md` - API specifications
- `docs/planning/processing_algorithm.md` - Processing algorithms
- `docs/planning/implementation_roadmap.md` - Implementation plan
- `prompts/completed/02_PLAN_extraction_pipeline.md` - Planning phase summary

**Design Decisions**
- Two-pass vs single-pass processing modes
- Wide-format table schema
- Unit ID assignment strategy
- Parquet output format
- Parallel processing architecture

---

## [0.2.0] - 2026-01-22

### Added - Research Phase Complete

**Research Documentation**
- `docs/research/00_RESEARCH_SUMMARY.md` - Complete research summary
- `docs/research/pysc2_api_reference.md` - pysc2 API documentation
- `docs/research/unit_tracking_strategy.md` - Unit tracking approach
- `docs/research/parallel_processing_approach.md` - Parallelization strategy

**Research Examples**
- `research_examples/01_basic_replay_loading.py` - Load and iterate replay
- `research_examples/02_extract_unit_data.py` - Extract units
- `research_examples/03_extract_economy_upgrades.py` - Extract economy/upgrades

**Findings**
- pysc2 observation structure documented
- Unit tracking approach validated
- Performance benchmarks established
- Parallel processing feasibility confirmed

---

## [0.1.0] - 2026-01-20

### Added - Initial Project Setup

**Project Foundation**
- Initial project structure
- Git repository setup
- Basic documentation
- Research phase initiated

**Infrastructure**
- Python virtual environment configuration
- Dependency management setup
- Development environment guidelines

---

## Version History Summary

| Version | Phase | Status | Lines of Code |
|---------|-------|--------|---------------|
| 1.0.0 | Phase 7: Documentation | ✅ Complete | ~15,000 words |
| 0.9.0 | Phase 6: Testing | ✅ Complete | ~3,000 lines |
| 0.8.0 | Phase 4: Validation | ✅ Complete | ~1,366 lines |
| 0.7.0 | Phase 3: Integration | ✅ Complete | ~848 lines |
| 0.6.0 | Phase 2: Extraction | ✅ Complete | ~1,929 lines |
| 0.5.0 | Phase 1: Extractors | ✅ Complete | ~730 lines |
| 0.4.0 | Infrastructure | ✅ Complete | ~500 lines |
| 0.3.0 | Planning | ✅ Complete | Documentation |
| 0.2.0 | Research | ✅ Complete | Documentation |
| 0.1.0 | Initial | ✅ Complete | Setup |

**Total Production Code**: ~5,373 lines
**Total Test Code**: ~3,000 lines
**Total Documentation**: ~20,000 words

---

## Breaking Changes

### None (v1.0.0 is first stable release)

Future breaking changes will be documented here with migration guides.

---

## Migration Guides

### Future migrations will be documented here

---

## Deprecations

### None currently

---

## Known Issues

### None blocking for v1.0.0

See [GitHub Issues](https://github.com/yourusername/local-play-bootstrap-main/issues) for open issues.

---

## Future Roadmap

### Potential Future Features

- **v1.1.0**: CLI interface with progress bars
- **v1.2.0**: Streaming processing mode for very large replays
- **v1.3.0**: Database backend option (PostgreSQL/SQLite)
- **v1.4.0**: Real-time replay processing
- **v1.5.0**: Additional feature extractors (camera, APM, engagement detection)
- **v2.0.0**: Cloud deployment support (AWS/GCP/Azure)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute to this project.

---

## License

This project is licensed under the GPLv3 License - see [LICENSE](LICENSE) file for details.
