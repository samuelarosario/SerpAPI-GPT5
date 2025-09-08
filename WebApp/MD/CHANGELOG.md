# WebApp Changelog

All notable changes to the WebApp will be documented here.

## [Unreleased]

### Fixed
- Resolved 500 errors on `/auth/me` caused by `EmailStr` validation rejecting internal demo accounts (`user@local`, `admin@local`). Relaxed `UserRead.email` to plain `str` while keeping `UserCreate.email` strict.

### Added / Changed
- Documented allowance for internal no-TLD emails in responses (demo/testing convenience). Production registration still enforces real email formats.
- Scaffold directory structure.
- Add README outlining goals and planned architecture.
- (Next) Introduce FastAPI app & authentication models.
