# Live experiment results (2026-07-20)

Environment: JDK 17.0.19 (jdk.attach + libattach.so present), jcmd/jps available, no JNLP
launcher preinstalled (portable IcedTea-Web 1.8.8 downloaded, no root). All under xvfb.

## 1. Swing runtime attach (exp_swing_attach.py) — PASS
Plain `java -jar swing-test-app.jar` (NO -javaagent) → VirtualMachine.attach(pid).loadAgent →
agent RPC port up in 0.4s → get_ui_tree = 137 nodes, find_elements('JButton') = 18. Full
introspection works with no launch-time flag.

## 2. SWT runtime attach + toolkit=auto (exp_swt_attach_rawrpc.py) — PASS
Plain SWT fat-jar → attach with toolkit=auto → agent log: "Detected SWT via loaded class:
org.eclipse.swt.internal.gtk3.GdkEventMotion" → "Using toolkit: swt". getUiGeneration ok,
getComponentTree = 16.7 KB (3 roots). The premain "defaults to Swing" limitation dissolves at
attach-time because SWT classes are already loaded.

## 3. JNLP end-to-end via IcedTea-Web (jnlp_topology_observe.py) — PARTIAL, key findings
- Self-hosted minimal Swing JNLP (sample_minimal.jnlp) served over http.server, launched via
  `java @itw-modularjdk.args -cp javaws.jar net.sourceforge.jnlp.runtime.Boot app.jnlp` under xvfb.
  ITW 1.8.8 runs on JDK 17 (harmless module warnings). App launched: log "Starting application
  [testapp.SwingTestApp] ...".
- TOPOLOGY FINDING (corrects desk research): ITW ran the app IN-PROCESS — ONE java pid, no fork —
  because the JNLP requested no launcher-mismatched vm-args. ITW forks a child app JVM only when
  the JNLP demands JVM args the launcher lacks. So "javaws always forks a child" is false; the
  topology is conditional.

## 4. Attach to sandboxed ITW JNLP JVM (jnlp_securitymanager_capture.py) — BLOCKED (expected)
- ITW installs a SecurityManager (log: "System::setSecurityManager has been called by
  JNLPRuntime"). Attaching the agent failed: AgentInitializationException. App-JVM stderr shows
  the mechanism — infinite recursion in ITW's policy resolving the attach-loaded (foreign) agent
  code:
    JNLPSecurityManager.checkPermission -> getApplication -> ClassLoader.checkClassLoaderPermission
      -> checkPermission -> getApplication -> JNLPPolicy.getPermissions -> ... (repeats)
- So doPrivileged wrapping by us cannot fix it (it is ITW classifying OUR code that fails).
  Confirms research risk #3 empirically. This blocker is legacy: SecurityManager is deprecated
  (JDK 18) and cannot be enabled from JDK 24 (JEP 486); it does not apply to all-permissions apps
  or modern OpenWebStart-on-modern-JDK. Sandboxed-legacy-ITW is documented as unsupported/degraded.

## Side-finding: SpyCore SWT tree path is broken
SpyCore("swt").refresh() calls self.lib.get_ui_tree, but the Rust SwtLibrary has no get_ui_tree
(only JTree/Tree content getters) -> AttributeError. The spy dump-tree/find/suggest are broken for
SWT/RCP through SpyCore (masked: SWT spy tests self-skip; DBeaver probe used raw getComponentTree).
Fix folded into this change (task 6.1).
