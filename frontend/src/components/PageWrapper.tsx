import { Container } from "@mui/material";
import type { ContainerProps } from "@mui/material";

interface PageWrapperProps {
  children: React.ReactNode;
  maxWidth?: ContainerProps["maxWidth"];
  /** Set to true for full-bleed pages like Home that manage their own background */
  disableGutters?: boolean;
}

export default function PageWrapper({
  children,
  maxWidth = "lg",
  disableGutters = false,
}: PageWrapperProps) {
  return (
    <Container
      maxWidth={maxWidth}
      disableGutters={disableGutters}
      sx={{
        py: { xs: 2, sm: 3 },
        px: disableGutters ? 0 : { xs: 2, sm: 3 },
      }}
    >
      {children}
    </Container>
  );
}
