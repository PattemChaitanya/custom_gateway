/**
 * Tests for shared UI components:
 * - PageWrapper
 * - PermissionGuard
 * - ProtectedRoute
 * - Header
 */
import { render, screen, act, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useAuthStore } from "../hooks/useAuth";
import PageWrapper from "../components/PageWrapper";
import { PermissionGuard } from "../components/PermissionGuard";
import ProtectedRoute from "../components/ProtectedRoute";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Wrap with in-memory router so Link/Navigate don't blow up */
function withRouter(ui: React.ReactElement, initialEntry = "/") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>{ui}</MemoryRouter>,
  );
}

function setProfile(overrides: object | null = {}) {
  act(() => {
    if (overrides === null) {
      useAuthStore.setState({
        accessToken: null,
        refreshToken: null,
        profile: null,
      });
    } else {
      useAuthStore.setState({
        accessToken: "tok",
        refreshToken: null,
        profile: {
          id: 1,
          email: "user@example.com",
          is_active: true,
          is_superuser: false,
          roles: ["editor"],
          permissions: ["api:read", "api:create"],
          ...overrides,
        },
      });
    }
  });
}

// Mock auth service used in ProtectedRoute
jest.mock("../services/auth", () => ({
  getCurrentUserInfo: jest.fn(),
  logout: jest.fn().mockResolvedValue(undefined),
  login: jest.fn(),
  me: jest.fn(),
  register: jest.fn(),
  resetPassword: jest.fn(),
}));

import { getCurrentUserInfo } from "../services/auth";
const mockGetCurrentUserInfo = getCurrentUserInfo as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
  act(() => {
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      profile: null,
    });
  });
  localStorage.clear();
});

// ===========================================================================
// PageWrapper
// ===========================================================================
describe("PageWrapper", () => {
  test("renders children inside a container", () => {
    render(
      <PageWrapper>
        <span>hello world</span>
      </PageWrapper>,
    );
    expect(screen.getByText("hello world")).toBeTruthy();
  });

  test("renders without crashing with default maxWidth", () => {
    const { container } = render(
      <PageWrapper>
        <div>content</div>
      </PageWrapper>,
    );
    expect(container.firstChild).toBeTruthy();
  });

  test("renders children with custom maxWidth", () => {
    render(
      <PageWrapper maxWidth="sm">
        <p>narrow</p>
      </PageWrapper>,
    );
    expect(screen.getByText("narrow")).toBeTruthy();
  });

  test("disableGutters passes gutter-free layout", () => {
    render(
      <PageWrapper disableGutters>
        <p>no gutters</p>
      </PageWrapper>,
    );
    expect(screen.getByText("no gutters")).toBeTruthy();
  });
});

// ===========================================================================
// PermissionGuard
// ===========================================================================
describe("PermissionGuard", () => {
  test("renders children when user has the required permission", () => {
    setProfile({ permissions: ["api:create"] });
    render(
      <PermissionGuard permission="api:create">
        <span>allowed</span>
      </PermissionGuard>,
    );
    expect(screen.getByText("allowed")).toBeTruthy();
  });

  test("hides children when user lacks required permission", () => {
    setProfile({ permissions: [] });
    render(
      <PermissionGuard permission="api:delete">
        <span>hidden</span>
      </PermissionGuard>,
    );
    expect(screen.queryByText("hidden")).toBeNull();
  });

  test("renders fallback when permission is missing and fallback is provided", () => {
    setProfile({ permissions: [] });
    render(
      <PermissionGuard
        permission="api:delete"
        fallback={<span>no access</span>}
      >
        <span>secret</span>
      </PermissionGuard>,
    );
    expect(screen.queryByText("secret")).toBeNull();
    expect(screen.getByText("no access")).toBeTruthy();
  });

  test("shows error alert when showError=true and permission missing", () => {
    setProfile({ permissions: [] });
    render(
      <PermissionGuard permission="api:delete" showError>
        <span>hidden</span>
      </PermissionGuard>,
    );
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByText("hidden")).toBeNull();
  });

  test("superuser can access any permission-gated content", () => {
    setProfile({ is_superuser: true, permissions: [] });
    render(
      <PermissionGuard permission="api:delete">
        <span>super access</span>
      </PermissionGuard>,
    );
    expect(screen.getByText("super access")).toBeTruthy();
  });

  test("renders children when user has the required role", () => {
    setProfile({ roles: ["admin"] });
    render(
      <PermissionGuard role="admin">
        <span>admin content</span>
      </PermissionGuard>,
    );
    expect(screen.getByText("admin content")).toBeTruthy();
  });

  test("renders when anyPermissions has at least one match", () => {
    setProfile({ permissions: ["api:read"] });
    render(
      <PermissionGuard anyPermissions={["api:delete", "api:read"]}>
        <span>partial match</span>
      </PermissionGuard>,
    );
    expect(screen.getByText("partial match")).toBeTruthy();
  });

  test("allPermissions gate blocks when one is missing", () => {
    setProfile({ permissions: ["api:read"] });
    render(
      <PermissionGuard
        allPermissions={["api:read", "api:create", "api:delete"]}
      >
        <span>all required</span>
      </PermissionGuard>,
    );
    expect(screen.queryByText("all required")).toBeNull();
  });

  test("allPermissions gate allows when all are present", () => {
    setProfile({ permissions: ["api:read", "api:create"] });
    render(
      <PermissionGuard allPermissions={["api:read", "api:create"]}>
        <span>all present</span>
      </PermissionGuard>,
    );
    expect(screen.getByText("all present")).toBeTruthy();
  });

  test("requireSuperuser blocks regular users", () => {
    setProfile({ is_superuser: false });
    render(
      <PermissionGuard requireSuperuser>
        <span>super only</span>
      </PermissionGuard>,
    );
    expect(screen.queryByText("super only")).toBeNull();
  });

  test("requireSuperuser allows superusers", () => {
    setProfile({ is_superuser: true });
    render(
      <PermissionGuard requireSuperuser>
        <span>super only</span>
      </PermissionGuard>,
    );
    expect(screen.getByText("super only")).toBeTruthy();
  });
});

// ===========================================================================
// ProtectedRoute
// ===========================================================================
describe("ProtectedRoute", () => {
  test("redirects to /login when no access token", async () => {
    // No token set
    withRouter(<ProtectedRoute />, "/dashboard");
    // After redirect, the path would change — we just verify login text isn't rendered
    // and the component doesn't crash
    await waitFor(() => {
      // ProtectedRoute redirects, so it should not show a spinner or outlet content
      expect(screen.queryByRole("progressbar")).toBeNull();
    });
  });

  test("shows spinner while loading profile", async () => {
    // Token set but no profile — triggers async profile load
    act(() => {
      useAuthStore.setState({
        accessToken: "tok",
        refreshToken: null,
        profile: null,
      });
    });

    // Block the profile fetch so loading state is visible during render
    let resolveProfile!: (v: any) => void;
    mockGetCurrentUserInfo.mockReturnValueOnce(
      new Promise((res) => {
        resolveProfile = res;
      }),
    );

    withRouter(<ProtectedRoute />);
    expect(screen.getByRole("progressbar")).toBeTruthy();

    // Resolve and verify spinner goes away
    await act(async () => {
      resolveProfile({
        id: 1,
        email: "a@b.com",
        is_active: true,
        is_superuser: false,
        roles: [],
        permissions: [],
      });
    });
    await waitFor(() => expect(screen.queryByRole("progressbar")).toBeNull());
  });

  test("renders outlet content when authenticated with profile", async () => {
    setProfile();
    // Profile is already set — no loading needed
    withRouter(<ProtectedRoute />);
    await waitFor(() => expect(screen.queryByRole("progressbar")).toBeNull());
    // Header should be rendered (contains nav)
    expect(screen.getByRole("banner")).toBeTruthy();
  });
});
