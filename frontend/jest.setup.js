require('@testing-library/jest-dom');

// start MSW server if available
try {
	const { server } = require('./src/mocks/server');
	beforeAll(() => server.listen());
	afterEach(() => server.resetHandlers());
	afterAll(() => server.close());
} catch (e) {
	// msw not installed in some environments
}
